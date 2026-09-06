! Experimental serial HRU coupling. Enable explicitly with SWAT_SHAW=1.
! SHAW owns canopy, snow, vertical water/heat, ET and runoff on eligible HRUs.
! SWAT+ owns management, plant structure, constituents and downstream routing.
module shaw_swat_module
  use iso_fortran_env, only: real64
  use shaw_column_api
  use hru_module, only: hru, surfq, latq, sepbtm, canstor, precip_eff, ep_day, es_day, canev, &
    ep_max, pet_day, snofall, snomlt, qtile, ihru
  use soil_module, only: soil
  use plant_module, only: pcom
  use organic_mineral_mass_module, only: pl_mass
  use hydrograph_module, only: irrig, ob
  use climate_module, only: w, wst, wgn, wgn_pms
  use time_module, only: time
  implicit none
  private
  public :: shaw_active, shaw_swat_day, shaw_plant_uptake
  type column_hru
    type(shaw_column) :: c
    logical :: initialized=.false.
    real, allocatable :: overlap(:,:), width(:), exported(:), uptake(:)
    real :: transp=0.
  end type
  type(column_hru), allocatable, save :: columns(:)
  logical, allocatable, save :: enabled(:)
  logical, save :: configured=.false., requested=.false.
  integer, save :: diag=0
contains
  logical function shaw_active(j) result(active)
    integer,intent(in)::j
    integer::i,u,stat,selected_hru,read_stat
    character(20)::setting
    character(80)::reason
    if(.not.configured) then
      call get_environment_variable('SWAT_SHAW',setting,status=stat)
      requested=stat==0.and.trim(setting)=='1'
      configured=.true.
      if(requested) then
        selected_hru=0
        call get_environment_variable('SWAT_SHAW_HRU',setting,status=stat)
        if(stat==0.and.len_trim(setting)>0) then
          read(setting,*,iostat=read_stat) selected_hru
          if(read_stat/=0.or.selected_hru<1.or.selected_hru>size(hru)) error stop 'Invalid SWAT_SHAW_HRU selection'
        endif
        if(time%step/=1) error stop 'SHAW bridge currently requires daily SWAT forcing'
        allocate(columns(size(hru)),enabled(size(hru)))
        open(newunit=u,file='shaw_hru_scope.csv',status='replace')
        write(u,'(a)') 'hru,area_ha,coupled,reason'
        enabled=.false.
        do i=1,size(hru)
          if(hru(i)%area_ha<=0.) cycle ! SWAT allocates an extra dummy HRU.
          reason='eligible'
          if(selected_hru>0.and.i/=selected_hru) reason='user scope selection'
          if(hru(i)%luse%urb_lu>0) reason='urban impervious surface'
          if(hru(i)%dbs%surf_stor>0) reason='surface water body'
          if(hru(i)%tiledrain>0) reason='tile drainage'
          if(hru(i)%septic>0) reason='septic system'
          enabled(i)=reason=='eligible'
          write(u,'(i0,",",f14.5,",",l1,",",a)') i,hru(i)%area_ha,enabled(i),trim(reason)
        enddo
        close(u)
        open(newunit=diag,file='shaw_hru_daily.csv',status='replace')
        write(diag,'(a)') 'year,jday,hru,precip_mm,external_soil_mm,surface_input_mm,et_mm,runoff_mm,'// &
          'percolation_mm,lateral_mm,storage_start_mm,storage_end_mm,residual_mm,swe_mm,ice_mm,tsoil_C,'// &
          'retry_hours,max_hour_parts,canopy_air_exchange_mm'
      endif
    endif
    active=.false.
    if(requested) active=enabled(j)
  end function

  subroutine initialize_hru(j)
    integer,intent(in)::j
    integer::n,nl,i,k,iw,ig
    real::depth,step,left,right,top,bot,weight,fc,wp,b,theta
    real::z(99),temp(99),water(99),rho(99),ks(99),kl(99),sand(99),silt(99),clay(99), &
      rock(99),om(99),ae(99),sat(99),exponent(99)
    real(real64)::expected
    associate(s=>columns(j))
      nl=soil(j)%nly
      depth=soil(j)%phys(nl)%d/1000.
      n=min(99,max(4,ceiling(depth/.05)+1))
      step=depth/(real(n)-1.5)
      allocate(s%overlap(n-1,nl),s%width(n-1),s%exported(nl),s%uptake(nl))
      s%overlap=0.;s%uptake=0.
      do i=1,n
        z(i)=real(i-1)*step
      enddo
      do i=1,n-1
        left=max(0.,z(i)-step/2.);right=z(i)+step/2.
        s%width(i)=right-left
        do k=1,nl
          bot=soil(j)%phys(k)%d/1000.
          top=bot-soil(j)%phys(k)%thick/1000.
          s%overlap(i,k)=max(0.,min(right,bot)-max(left,top))
        enddo
      enddo
      do k=1,nl
        if(abs(sum(s%overlap(:,k))*1000.-soil(j)%phys(k)%thick)>.002) &
          error stop 'SHAW soil mapping does not conserve layer volume'
      enddo
      do i=1,n
        rho(i)=0.;ks(i)=0.;kl(i)=0.;sand(i)=0.;silt(i)=0.;clay(i)=0.;rock(i)=0.;om(i)=0.
        water(i)=0.;temp(i)=0.;sat(i)=0.;fc=0.;wp=0.
        do k=1,nl
          weight=0.
          if(i<n) then
            weight=s%overlap(i,k)/s%width(i)
          else if(k==nl) then
            weight=1.
          endif
          rho(i)=rho(i)+weight*soil(j)%phys(k)%bd*1000.
          ks(i)=ks(i)+weight*max(soil(j)%phys(k)%k,1.e-5)/3600000.
          ! Native lateral term is Klat * slope * cell thickness. Divide by
          ! HRU hillslope length to convert discharge per width to areal depth.
          ! Non-tiled SWAT HRUs do not initialize ly%conk (it belongs to the
          ! tile routine). Assume isotropic K and retain the HRU lateral multiplier.
          kl(i)=kl(i)+weight*max(0.,soil(j)%phys(k)%k)*max(0.,hru(j)%hyd%latq_co)/ &
            3600000./max(1.,hru(j)%topo%lat_len)
          sand(i)=sand(i)+weight*soil(j)%phys(k)%sand/100.
          clay(i)=clay(i)+weight*soil(j)%phys(k)%clay/100.
          silt(i)=silt(i)+weight*soil(j)%phys(k)%silt/100.
          rock(i)=rock(i)+weight*soil(j)%phys(k)%rock/100.
          om(i)=om(i)+weight*min(.5,soil(j)%phys(k)%cbn*.01724)
          sat(i)=sat(i)+weight*soil(j)%phys(k)%por
          fc=fc+weight*(soil(j)%phys(k)%fc+soil(j)%phys(k)%wpmm)/soil(j)%phys(k)%thick
          wp=wp+weight*soil(j)%phys(k)%wp
          theta=(soil(j)%phys(k)%st+soil(j)%phys(k)%wpmm)/soil(j)%phys(k)%thick
          water(i)=water(i)+weight*theta
          temp(i)=temp(i)+weight*soil(j)%phys(k)%tmp
        enddo
        if(wp<=0..or.fc<=wp.or.fc>=sat(i)) error stop 'Invalid initialized SWAT retention points'
        b=log(153./3.36)/log(fc/wp)
        exponent(i)=b
        ae(i)=-3.36*(fc/sat(i))**b
      enddo
      iw=ob(hru(j)%obj_no)%wst;ig=wst(iw)%wco%wgn
      ! Constant lower boundary from the initial profile, without adding a hidden soil reservoir.
      call shaw_initialize(s%c,n,z(1:n),temp(1:n),water(1:n),real(wgn(ig)%lat,real64), &
        real(hru(j)%topo%elev,real64))
      call shaw_set_soil_parameters(s%c,rho,ks,kl,sand,silt,clay,rock,om,ae,sat,exponent)
      call shaw_set_solver_tolerance(s%c,1.e-4,1.e-4)
      call shaw_correct_canopy_jacobian(s%c,.true.)
      s%c%soitmp=wgn_pms(ig)%tmp_an
      s%c%slope=atan(max(0.,hru(j)%topo%slope))
      s%c%clouds=.5
      expected=0.
      do k=1,nl
        expected=expected+real(soil(j)%phys(k)%st+soil(j)%phys(k)%wpmm,real64)
        s%exported(k)=soil(j)%phys(k)%st
      enddo
      if(abs(shaw_soil_storage(s%c)*1000.-expected)>.005) error stop 'SHAW initial water mapping error'
      if(hru(j)%sno_mm>1.e-5.or.canstor(j)>1.e-5) &
        error stop 'SHAW bridge requires snow-free and empty-canopy initial state'
      s%initialized=.true.
    end associate
  end subroutine

  subroutine shaw_swat_day(j)
    integer,intent(in)::j
    integer::i,k,h,n,nl,retry_hours,max_parts
    real::delta(99),external,overflow,solar(24),decl,lat,angle,temp,precip,surface_input,lai,root,height,mass
    real::flux(320),water,ice,netet,runoff,perc,lateral,frac
    real(real64)::before,after,residual
    if(.not.shaw_active(j)) return
    if(.not.columns(j)%initialized) call initialize_hru(j)
    associate(s=>columns(j),c=>columns(j)%c)
      n=c%ns;nl=soil(j)%nly
      before=shaw_storage(c)*1000.
      delta=0.;external=0.
      do k=1,nl
        water=soil(j)%phys(k)%st-s%exported(k)
        external=external+water
        do i=1,n-1
          delta(i)=delta(i)+s%overlap(i,k)/s%width(i)*water/soil(j)%phys(k)%thick
        enddo
      enddo
      overflow=0.
      if(any(abs(delta(1:n-1))>1.e-9)) call shaw_add_water(c,delta,overflow)
      lai=0.;root=.05;height=.02;mass=0.
      do k=1,pcom(j)%npl
        lai=lai+pcom(j)%plg(k)%lai
        root=max(root,pcom(j)%plg(k)%root_dep/1000.)
        height=max(height,pcom(j)%plg(k)%cht)
        mass=mass+pl_mass(j)%ab_gr(k)%m/10000.
      enddo
      call shaw_set_vegetation(c,lai,height,mass,root)
      decl=.4093*sin(2.*acos(-1.)*(real(time%day)-81.)/365.)
      lat=c%alatud
      do h=1,24
        angle=(real(h)-12.)*acos(-1.)/12.
        solar(h)=max(0.,sin(lat)*sin(decl)+cos(lat)*cos(decl)*cos(angle))
      enddo
      if(sum(solar)>0.) solar=solar/sum(solar)*max(0.,w%solrad)*1.e6/3600.
      surface_input=max(0.,precip_eff-w%precip)+max(0.,irrig(j)%applied-irrig(j)%runoff)
      precip=max(0.,w%precip)/24000.
      flux=0.;snofall=0.;retry_hours=0;max_parts=1
      do h=1,24
        temp=w%tave+(w%tmax-w%tmin)/2.*sin((real(h)-9.)*acos(-1.)/12.)
        if(temp<=0.) snofall=snofall+max(0.,w%precip)/24.
        call shaw_advance_hour(c,time%yrc,time%day,h,temp,real(w%rhum,real64),real(w%windsp,real64),solar(h),precip)
        if(c%flux(319)>1.) retry_hours=retry_hours+1
        max_parts=max(max_parts,nint(c%flux(319)))
        ! Runon/irrigation remain liquid and bypass atmospheric rain/snow partition.
        ! Add at the interval end; retained pond water enters the next SHAW step.
        c%pond=c%pond+surface_input/24000.
        flux=flux+c%flux
      enddo
      netet=-flux(2)*1000.;runoff=flux(1)*1000.+overflow*1000.
      perc=flux(20+n-1)*1000.;lateral=sum(flux(120:118+n))*1000.
      after=shaw_storage(c)*1000.
      ! Growing, emerging or snow-buried canopy changes the atmospheric control
      ! volume. Book its vapor mass separately from physical evaporation/rain.
      residual=after-before-w%precip-surface_input-external-flux(318)*1000.+netet+runoff+perc+lateral
      s%uptake=0.;ice=0.
      soil(j)%sw=0.
      do k=1,nl
        water=0.;soil(j)%phys(k)%tmp=0.;soil(j)%ly(k)%flat=0.
        do i=1,n-1
          water=water+s%overlap(i,k)*c%vlcdt(i)*1000.
          ice=ice+s%overlap(i,k)*c%vicdt(i)*920.
          soil(j)%phys(k)%tmp=soil(j)%phys(k)%tmp+ &
            s%overlap(i,k)*1000./soil(j)%phys(k)%thick*c%tsdt(i)
          frac=s%overlap(i,k)/s%width(i)
          soil(j)%ly(k)%flat=soil(j)%ly(k)%flat+frac*flux(119+i)*1000.
          s%uptake(k)=s%uptake(k)+frac*flux(218+i)
        enddo
        soil(j)%phys(k)%st=max(0.,water-soil(j)%phys(k)%wpmm)
        soil(j)%sw=soil(j)%sw+soil(j)%phys(k)%st
        s%exported(k)=soil(j)%phys(k)%st
        ! Signed vertical flux interpolated to the original horizon bottom.
        angle=soil(j)%phys(k)%d/1000./(c%zs(2)-c%zs(1))+.5
        i=min(n-1,max(1,int(angle)))
        frac=max(0.,min(1.,angle-real(i)))
        soil(j)%ly(k)%prk=1000.*((1.-frac)*flux(20+i)+frac*flux(20+min(n-1,i+1)))
      enddo
      hru(j)%sno_mm=real(shaw_swe(c)*1000.)
      canstor(j)=sum(c%pcandt)*1000.
      surfq(j)=runoff;sepbtm(j)=perc;latq(j)=lateral;qtile=0.
      snomlt=flux(4)*1000.
      s%transp=flux(3)*1000.;ep_day=s%transp
      ! Aggregate residual ET includes canopy/snow evaporation and dew.
      ! Component-specific esoil/ecanopy are not physically separated in this first bridge.
      es_day=netet-ep_day;canev=0.
      ep_max=max(0.,pet_day)*min(1.,lai/3.)
      write(diag,'(i0,2(",",i0),16(",",es18.9))') time%yrc,time%day,j,w%precip,external, &
        surface_input,netet,runoff,perc,lateral,before,after,residual,hru(j)%sno_mm,ice,soil(j)%phys(1)%tmp, &
        real(retry_hours),real(max_parts),flux(318)*1000.
      if(abs(residual)>.1_real64) then
        flush(diag)
        write(*,*) 'SHAW water residual > 0.1 mm: year/day/HRU/residual',time%yrc,time%day,j,residual
        error stop 'SHAW daily water conservation gate failed'
      endif
    end associate
  end subroutine

  subroutine shaw_plant_uptake(j,ip,potential)
    integer,intent(in)::j,ip
    real(kind=4),intent(in)::potential ! SWAT+ public boundary remains binary32.
    real::fraction,total_lai,actual
    integer::k
    total_lai=0.
    do k=1,pcom(j)%npl
      total_lai=total_lai+pcom(j)%plg(k)%lai
    enddo
    fraction=pcom(j)%plg(ip)%lai/max(1.e-8,total_lai)
    actual=columns(j)%transp*fraction
    pcom(j)%plcur(ip)%uptake(:)=columns(j)%uptake(:)*fraction
    pcom(j)%plstr(ip)%strsw=1.
    if(potential>1.e-6) pcom(j)%plstr(ip)%strsw=max(0.,min(1.,actual/potential))
  end subroutine
end module

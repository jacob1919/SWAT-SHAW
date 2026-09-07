! In-memory serial interface to USDA-ARS SHAW 3.0.3 water/heat physics.
module shaw_column_api
  use iso_fortran_env, only: real64
  use ieee_arithmetic, only: ieee_is_finite
  use shaw_column_types
  use shaw_common_access
  implicit none
  private
  public :: shaw_column, shaw_initialize, shaw_advance_hour, shaw_storage, shaw_swe, shaw_soil_storage
  public :: shaw_set_soil_parameters, shaw_set_vegetation
  public :: shaw_add_water
  public :: shaw_set_solver_tolerance
  public :: shaw_correct_canopy_jacobian
  public :: shaw_snowfall_input
  type(shaw_snapshot), save :: pristine
  logical, save :: template_ready = .false.
contains
  real function shaw_snowfall_input(c) result(snow)
    type(shaw_column),intent(in) :: c
    real :: threshold_temperature
    ! Atmospheric input classified by the same threshold as native PRECP.
    ! Report before canopy interception; exclude remobilized old snow/pond.
    threshold_temperature=c%tmpday
    if(c%isnotmp/=1) then
      call shaw_load_state(c%memory)
      call SHP_WTBULB(threshold_temperature,c%tmpday,c%humday)
    endif
    snow=0.
    if(threshold_temperature<=c%snotmp.or.c%snoden>0.) snow=c%precip
  end function
  subroutine shaw_correct_canopy_jacobian(c, enabled)
    type(shaw_column),intent(inout)::c
    logical,intent(in)::enabled
    call shaw_load_state(c%memory)
    options_canopy_jacobian=merge(1,0,enabled)
    call shaw_save_state(c%memory)
  end subroutine
  subroutine shaw_set_solver_tolerance(c, tolerance, canopy_water_tolerance)
    type(shaw_column),intent(inout)::c
    real,intent(in)::tolerance,canopy_water_tolerance
    if(tolerance<=0..or.canopy_water_tolerance<=0.) error stop 'Nonpositive SHAW solver tolerance'
    c%toler=tolerance
    call shaw_load_state(c%memory)
    options_canopy_water_tol=canopy_water_tolerance
    call shaw_save_state(c%memory)
  end subroutine
  subroutine shaw_add_water(c, delta, overflow)
    type(shaw_column), intent(inout) :: c
    real, intent(in) :: delta(:) ! Volumetric liquid increment at each active node.
    real, intent(out) :: overflow ! m; positive additions exceeding pore space.
    real :: excess, dz, dummy
    integer :: i
    overflow=0.
    call shaw_load_state(c%memory)
    do i=1,c%ns-1
      dz=(c%zs(i+1)-c%zs(max(1,i-1)))/2.
      c%vlcdt(i)=c%vlcdt(i)+delta(i)
      if(c%vlcdt(i)<1.e-8) error stop 'External SWAT withdrawal exceeds SHAW liquid storage'
      excess=max(0.,c%vlcdt(i)+.92*c%vicdt(i)-slparm_soilwrc(i,2))
      c%vlcdt(i)=c%vlcdt(i)-excess
      overflow=overflow+excess*dz
      call SHP_MATVL1(i,c%matdt(i),c%vlcdt(i),dummy)
      ! Added water has the receiving soil temperature; partition at that temperature.
      call SHP_FROZEN(i,c%vlcdt,c%vicdt,c%matdt,c%concdt,c%tsdt,c%saltdt,c%icesdt)
    enddo
    call shaw_save_state(c%memory)
  end subroutine
  subroutine shaw_initialize(c, n, z, temperature, water, latitude, elevation)
    type(shaw_column), intent(out) :: c
    integer, intent(in) :: n
    real, intent(in) :: z(n), temperature(n), water(n), latitude, elevation
    if (n < 3 .or. n > 99) error stop 'SHAW requires 3..99 soil nodes'
    if(storage_size(0.)/=64.or.storage_size(0)/=32) error stop 'SHAW snapshot requires REAL64 / INTEGER32'
    if (any(z(2:n) <= z(1:n-1)) .or. z(1) /= 0.) error stop 'Invalid SHAW grid'
    if (.not. template_ready) then
      call shaw_save_state(pristine)
      template_ready = .true.
    end if
    c = shaw_column()
    c%memory = pristine
    call shaw_load_state(c%memory)
    slparm_nsalt = 0
    slparm_iwrc = 1
    slparm_saltkq = 0.
    options_canopy_water_tol=0.01 ! Original SHAW canopy-vapor stopping criterion.
    options_canopy_jacobian=0 ! Preserve original numerical path unless explicitly enabled.
    constn_presur = 101300. * exp(-elevation/8278.)
    c%ns = n
    c%zs(1:n) = z
    c%tsdt(1:n) = temperature
    c%vlcdt(1:n) = water
    c%nhrpdt = 1
    c%dtime = 3600.
    c%wwdt = 0.6
    c%toler = 0.001
    c%ivlcbc = 1                    ! Free drainage (unit gradient).
    c%itmpbc = 0                    ! Prescribed deep temperature.
    c%soitmp = temperature(n)
    c%vlcday = water(n)
    c%albdry = 0.15
    c%albexp = 0.
    c%zmsrf = 0.006
    c%zhsrf = 0.0012
    c%zmsp = 0.001
    c%zhsp = 0.0002
    c%height = 2.
    c%pondmx = 0.
    c%alatud = latitude * acos(-1.)/180.
    c%hrnoon = 12.
    c%isnotmp = 0
    c%canma = -53.72
    c%canmb = 1.32
    c%istomate = 1
    c%xangle = 1.
    c%clumpng = 1.
    c%canalb = 0.25
    c%tccrit = 7.
    c%rstom0 = 100.
    c%rstexp = 5.
    c%pleaf0 = -300.
    c%rleaf0 = 1./6.7e5
    c%rroot0 = 1./1.7e6
    c%pintrcp = 0.001
    c%dchar = 0.005
    c%gmcmax = 3.
    call shaw_save_state(c%memory)
  end subroutine

  subroutine shaw_set_soil_parameters(c, density, ksat, klat, sand, silt, clay, rock, om, air_entry, saturation, exponent)
    type(shaw_column), intent(inout) :: c
    real, intent(in) :: density(:), ksat(:), klat(:), sand(:), silt(:), clay(:), rock(:), om(:)
    real, intent(in) :: air_entry(:), saturation(:), exponent(:)
    integer :: n
    n=c%ns
    if (any(density(1:n)<=0.) .or. any(ksat(1:n)<=0.) .or. any(saturation(1:n)<=0.) .or. &
        any(air_entry(1:n)>=0.) .or. any(exponent(1:n)<=0.)) error stop 'Invalid SHAW soil parameters'
    call shaw_load_state(c%memory)
    slparm_rhob(1:n)=density(1:n)
    slparm_satk(1:n)=ksat(1:n)
    slparm_satklat(1:n)=klat(1:n)
    slparm_sand(1:n)=sand(1:n)
    slparm_silt(1:n)=silt(1:n)
    slparm_clay(1:n)=clay(1:n)
    slparm_rock(1:n)=rock(1:n)
    slparm_om(1:n)=om(1:n)
    slparm_soilwrc(1:n,1)=air_entry(1:n)
    slparm_soilwrc(1:n,2)=saturation(1:n)
    slparm_soilwrc(1:n,3)=exponent(1:n)
    slparm_soilwrc(1:n,4)=0.
    call shaw_save_state(c%memory)
  end subroutine

  subroutine shaw_set_vegetation(c, lai, height, mass, root_depth)
    type(shaw_column), intent(inout) :: c
    real, intent(in) :: lai, height, mass, root_depth
    ! A single effective live canopy. Structural states come from SWAT+;
    ! stomatal/hydraulic parameters are explicit defaults, not calibrated values.
    c%nplant=1
    c%itype(1)=1
    c%pltlai(1)=max(0.,lai)
    ! Harvest/leaf fall must not discard existing intercepted water.
    if(lai<=0.) then
      c%pond=c%pond+sum(c%pcandt)
      c%pcandt=0.
    endif
    c%plthgt(1)=max(0.02,height)
    c%pltwgt(1)=max(0.001,mass)
    c%rootdp(1)=max(0.01,min(root_depth,c%zs(c%ns-1)))
    c%height=max(2.,height+2.)
  end subroutine

  subroutine shaw_advance_hour(c, year, day, hour, temperature, humidity, wind, solar, precip)
    type(shaw_column), intent(inout) :: c
    integer, intent(in) :: year,day,hour
    real, intent(in) :: temperature,humidity,wind,solar,precip
    real :: decl, cos_halfday, integrated(320)
    type(shaw_column) :: start
    integer :: parts,part,dump_unit,strategy,strategies,requested_option
    logical :: converged
    c%year=year
    c%julian=day
    c%hour=hour
    c%tmpday=temperature
    c%humday=max(0.001,min(1.,humidity))
    c%winday=max(0.1,wind)
    c%sunhor=max(0.,solar)
    c%precip=max(0.,precip)
    c%snoden=0.
    decl=0.4093*sin(2.*acos(-1.)*(real(day)-81.)/365.)
    c%declin=decl
    cos_halfday=-tan(c%alatud)*tan(decl)
    c%hafday=acos(max(-1.,min(1.,cos_halfday)))
    start=c
    call shaw_load_state(start%memory)
    requested_option=options_canopy_jacobian
    strategies=0
    if(requested_option==1) strategies=1
    parts=1
    do
      do strategy=0,strategies
        ! Both Jacobians solve the same residuals with the same stopping tests.
        ! Each attempt starts from the complete hour snapshot, including SAVE.
        c=start
        if(strategy==1) then
          call shaw_load_state(c%memory)
          options_canopy_jacobian=2
          call shaw_save_state(c%memory)
        endif
        c%dtime=3600./real(parts)
        c%precip=start%precip/real(parts)
        integrated=0.
        converged=.true.
        do part=1,parts
          call shaw_call(c)
          if(c%flux(320)<0.) then
            converged=.false.
            exit
          endif
          integrated=integrated+c%flux
        enddo
        if(converged) exit
      enddo
      if(converged) exit
      parts=parts*2
      if(parts>64) then
        c=start
        open(newunit=dump_unit,file='shaw_failed_column.bin',access='stream',form='unformatted',status='replace')
        write(dump_unit) start
        close(dump_unit)
        write(*,*) 'SHAW retry limit: year/day/hour',year,day,hour
        error stop 'SHAW did not converge after time-step refinement'
      endif
    enddo
    c%flux=integrated
    c%flux(319)=real(parts)
    c%flux(320)=real(strategy) ! Accepted hour used the additional conductance Jacobian.
    call shaw_load_state(c%memory)
    options_canopy_jacobian=requested_option
    call shaw_save_state(c%memory)
    c%dtime=3600.
    c%precip=start%precip
    if (.not. all(ieee_is_finite(c%tsdt(1:c%ns))) .or. &
        .not. all(ieee_is_finite(c%vlcdt(1:c%ns))) .or. &
        .not. all(ieee_is_finite(c%vicdt(1:c%ns))) .or. &
        .not. all(ieee_is_finite(c%flux))) error stop 'Nonfinite SHAW state/flux'
    if (minval(c%vlcdt(1:c%ns)) < -1.e-6 .or. minval(c%vicdt(1:c%ns)) < -1.e-6) &
        error stop 'Negative SHAW liquid/ice'
  end subroutine

  real(real64) function shaw_soil_storage(c) result(storage)
    type(shaw_column), intent(in) :: c
    real(real64) :: dz
    integer :: i
    storage=0._real64
    do i=1,c%ns-1
      if (i==1) then
        dz=real(c%zs(2)-c%zs(1),real64)/2.
      else
        dz=real(c%zs(i+1)-c%zs(i-1),real64)/2.
      end if
      storage=storage+dz*(real(c%vlcdt(i),real64)+0.92_real64*real(c%vicdt(i),real64))
    end do
  end function

  real(real64) function shaw_swe(c) result(storage)
    type(shaw_column), intent(in) :: c
    integer :: i
    storage=0._real64
    do i=1,c%nsp
      storage=storage+real(c%rhosp(i),real64)*real(c%dzsp(i),real64)/1000.+real(c%dlwdt(i),real64)
    end do
    if(c%nsp>0) storage=storage+real(c%store,real64)+sum(real(c%wlag,real64))
  end function

  real(real64) function shaw_storage(c) result(storage)
    type(shaw_column), intent(in) :: c
    integer :: i
    real(real64) :: dz
    storage=shaw_soil_storage(c)+shaw_swe(c)+real(c%pond,real64)+sum(real(c%pcandt,real64))
    do i=1,c%nc
      if(c%nc==1) then
        dz=real(c%zc(2)-c%zc(1),real64)
      else if(i==c%nc) then
        dz=real(c%zc(i+1)-c%zc(i),real64)+real(c%zc(i)-c%zc(i-1),real64)/2.
      else if(i==1) then
        dz=real(c%zc(2)-c%zc(1),real64)/2.
      else
        dz=real(c%zc(i+1)-c%zc(i-1),real64)/2.
      endif
      storage=storage+dz*real(c%vapcdt(i),real64)/1000.
    enddo
  end function
end module shaw_column_api

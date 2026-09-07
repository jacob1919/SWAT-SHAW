program test_shaw_canopy
  use iso_fortran_env, only: real64
  use shaw_column_api
  implicit none
  type(shaw_column) :: c,phase
  real :: z(21), temperature(21), water(21), density(21), k(21), zero(21)
  real :: sand(21), silt(21), clay(21), air_entry(21), saturation(21), exponent(21)
  real :: air, rain, solar, intercepted, old_pond
  real(real64) :: before, after, outward, residual, max_residual, air_exchange
  real(real64) :: max_swe, max_ice, structural_before
  integer :: i, t, h, u
  logical :: saw_bare, saw_single, saw_multiple, checked_leaf_removal

  do i=1,21
    z(i)=real(i-1)*.05
  enddo
  temperature=3.; water=.3; density=1300.; k=1.e-6; zero=0.
  sand=.4; silt=.4; clay=.2; air_entry=-.3; saturation=.48; exponent=4.5
  call shaw_initialize(c,21,z,temperature,water,45.25,106.)
  call shaw_set_soil_parameters(c,density,k,zero,sand,silt,clay,zero,zero,air_entry,saturation,exponent)
  call shaw_set_vegetation(c,0.,.8,.1,.6)
  call shaw_set_solver_tolerance(c,1.e-4,1.e-3)
  call shaw_correct_canopy_jacobian(c,.true.)
  c%clouds=.5
  max_residual=0.; air_exchange=0.; max_swe=0.; max_ice=0.
  saw_bare=.false.; saw_single=.false.; saw_multiple=.false.; checked_leaf_removal=.false.
  open(newunit=u,file='shaw_canopy_test.csv',status='replace')
  write(u,'(a)') 'hour,canopy_nodes,air_C,swe_mm,ice_mm,canopy_air_exchange_mm,water_residual_mm'

  do t=1,288
    before=shaw_storage(c)
    select case(t)
    case(25)
      ! Native CANLAY uses approximately LAI / 0.5 nodes; LAI 0.5 gives NC=1.
      call shaw_set_vegetation(c,.5,.8,.1,.6)
    case(49)
      call shaw_set_vegetation(c,4.,.8,.3,.6)
    case(73)
      call shaw_set_vegetation(c,4.,1.6,.5,.6)
    case(120)
      ! Rain in the previous hour supplies real intercepted water for harvest.
      intercepted=sum(c%pcandt)
      old_pond=c%pond
      if(intercepted<=1.e-8) error stop 'Canopy fixture did not retain water before leaf removal'
      structural_before=shaw_storage(c)
      call shaw_set_vegetation(c,0.,1.6,.5,.6)
      if(any(c%pcandt/=0.)) error stop 'Leaf removal did not clear interception'
      if(abs(c%pond-old_pond-intercepted)>1.e-12) error stop 'Leaf removal lost intercepted water'
      if(abs(shaw_storage(c)-structural_before)>1.e-12_real64) &
        error stop 'Leaf removal changes total storage before regridding'
      checked_leaf_removal=.true.
    case(121)
      call shaw_set_vegetation(c,.5,.8,.1,.6)
    case(145)
      call shaw_set_vegetation(c,4.,1.6,.5,.6)
    end select

    h=mod(t-1,24)+1
    if(t<=72.or.(t>=169.and.t<=216)) then
      air=-5.+2.*sin(real(h-8)*acos(-1.)/12.)
    else
      air=8.+3.*sin(real(h-8)*acos(-1.)/12.)
    endif
    solar=max(0.,200.*sin(real(h-6)*acos(-1.)/12.))
    rain=0.
    if(t==20.or.t==119.or.t==180) rain=.002
    call shaw_advance_hour(c,2020,20+(t-1)/24,h,air,.8,2.,solar,rain)
    after=shaw_storage(c)
    ! Atmospheric vapor is positive into the column; flux 318 is the signed
    ! air-water storage exchange caused solely by moving canopy boundaries.
    outward=real(c%flux(1)-c%flux(2)+c%flux(20+c%ns-1)+sum(c%flux(120:118+c%ns)),real64)
    residual=1000.*(after-before-real(rain,real64)-real(c%flux(318),real64)+outward)
    max_residual=max(max_residual,abs(residual))
    air_exchange=air_exchange+abs(real(c%flux(318),real64))*1000.
    max_swe=max(max_swe,shaw_swe(c)*1000.)
    max_ice=max(max_ice,maxval(real(c%vicdt(1:c%ns-1),real64)))
    saw_bare=saw_bare.or.c%nc==0
    saw_single=saw_single.or.c%nc==1
    saw_multiple=saw_multiple.or.c%nc>1
    write(u,'(i0,",",i0,5(",",es18.9))') t,c%nc,air,shaw_swe(c)*1000., &
      sum(c%vicdt(1:c%ns-1))*0.05*920.,c%flux(318)*1000.,residual
  enddo
  close(u)

  if(.not.(saw_bare.and.saw_single.and.saw_multiple)) error stop 'Canopy node transitions were not covered'
  if(.not.checked_leaf_removal) error stop 'Wet canopy leaf removal was not covered'
  if(max_swe<=0..or.max_ice<=1.e-8) error stop 'Snow and frozen soil were not covered'
  if(air_exchange<=1.e-8_real64) error stop 'Canopy geometry exchange was not exercised'
  if(max_residual>.002_real64) error stop 'Dynamic canopy hourly water residual exceeds 0.002 mm'
  phase=c; phase%precip=.001; phase%tmpday=2.; phase%humday=.1
  if(shaw_snowfall_input(phase)/=phase%precip) error stop 'Dry above-freezing air must use wet-bulb snow phase'
  phase%humday=1.
  if(shaw_snowfall_input(phase)/=0.) error stop 'Warm saturated air must classify liquid precipitation'
  phase%tmpday=-2.
  if(shaw_snowfall_input(phase)/=phase%precip) error stop 'Cold air must classify snowfall'
  print *, 'PASS: dynamic canopy, snow and freeze/thaw; max hourly water residual mm=',max_residual
end program test_shaw_canopy

program test_shaw_columns
  use iso_fortran_env, only: real64
  use shaw_column_api
  implicit none
  type(shaw_column) :: a,b,initial_a,initial_b,serial_a,serial_b
  real :: z(11), temp(11), water(11), density(11),k(11),zero(11),sand(11),silt(11),clay(11),ae(11),sat(11),exponent(11)
  real(real64) :: budget,max_budget,before,after,fluxout
  real :: increment(11),overflow
  integer :: i, t, u
  do i=1,11
    z(i)=real(i-1)*0.1
  enddo
  temp=3.;water=.30;density=1300.;k=1.e-6;zero=0.;sand=.4;silt=.4;clay=.2;ae=-.3;sat=.48;exponent=4.5
  call shaw_initialize(a,11,z,temp,water,45.25,106.)
  call shaw_set_soil_parameters(a,density,k,zero,sand,silt,clay,zero,zero,ae,sat,exponent)
  a%clouds=.5
  call shaw_set_vegetation(a,2.,.8,.3,.6)
  call shaw_set_forcing_height(a,a%plthgt(1)+2.)
  temp=-2.;water=.35
  call shaw_initialize(b,10,z(1:10),temp(1:10),water(1:10),45.25,180.)
  call shaw_set_soil_parameters(b,density,k*2.,zero,sand,silt,clay,zero,zero,ae,sat,exponent)
  b%clouds=.7
  call shaw_set_vegetation(b,4.,5.,2.,.8)
  call shaw_set_forcing_height(b,b%plthgt(1)+2.)
  call shaw_set_solver_tolerance(a,1.e-4,1.e-3)
  call shaw_set_solver_tolerance(b,1.e-4,1.e-3)
  call shaw_correct_canopy_jacobian(a,.true.)
  call shaw_correct_canopy_jacobian(b,.true.)
  initial_a=a;initial_b=b
  increment=0.001
  before=shaw_storage(a)
  call shaw_add_water(a,increment,overflow)
  if(abs(shaw_storage(a)-before-.00095_real64)>1.e-7.or.overflow/=0.) &
    error stop 'External liquid addition is not conservative'
  call shaw_add_water(a,-increment,overflow)
  if(abs(shaw_storage(a)-before)>1.e-7) error stop 'External withdrawal is not conservative'
  a=initial_a
  max_budget=0.
  open(newunit=u,file='shaw_column_test.csv',status='replace')
  write(u,'(a)') 'hour,temperature,liquid,ice,swe_mm,water_residual_mm'
  do t=1,240
    before=shaw_storage(a)
    call advance(a,t,1)
    after=shaw_storage(a)
    ! SHAW EVAP1 is positive INTO the column (negative evaporation).
    fluxout=real(a%flux(1)-a%flux(2)+a%flux(20+a%ns-1)+sum(a%flux(120:118+a%ns)),real64)
    budget=1000.*(after-before-real(a%precip,real64)-a%flux(318)+fluxout)
    max_budget=max(max_budget,abs(budget))
    write(u,'(i0,5(",",es18.9))') t,a%tsdt(1),a%vlcdt(1),a%vicdt(1),shaw_swe(a)*1000.,budget
  enddo
  close(u)
  serial_a=a
  do t=1,240
    call advance(b,t,2)
  enddo
  serial_b=b
  a=initial_a;b=initial_b
  do t=1,240
    call advance(a,t,1)
    call advance(b,t,2)
  enddo
  if(any(a%tsdt/=serial_a%tsdt).or.any(a%vlcdt/=serial_a%vlcdt).or.any(a%vicdt/=serial_a%vicdt)) &
    error stop 'Column A depends on HRU execution order'
  if(any(b%tsdt/=serial_b%tsdt).or.any(b%vlcdt/=serial_b%vlcdt).or.any(b%vicdt/=serial_b%vicdt)) &
    error stop 'Column B depends on HRU execution order'
  if(any(a%flux/=serial_a%flux).or.any(b%flux/=serial_b%flux)) error stop 'Flux depends on HRU execution order'
  if(max_budget>0.002_real64) error stop 'Hourly water balance residual exceeds 0.002 mm'
  print *, 'PASS: 2 independent and interleaved columns agree exactly; max hourly residual mm=',max_budget
contains
  subroutine advance(c,t,variant)
    type(shaw_column),intent(inout)::c
    integer,intent(in)::t,variant
    real::air,rain,solar
    integer::hour
    hour=mod(t-1,24)+1
    air=-6.+10.*sin(real(t)*acos(-1.)/120.)+3.*sin(real(hour-8)*acos(-1.)/12.)
    if(variant==2) air=air-2.
    solar=max(0.,200.*sin(real(hour-6)*acos(-1.)/12.))
    rain=0.
    if(mod(t,47)==0) rain=.002
    call shaw_advance_hour(c,2020,20+(t-1)/24,hour,air,.7,2.,solar,rain)
  end subroutine
end program

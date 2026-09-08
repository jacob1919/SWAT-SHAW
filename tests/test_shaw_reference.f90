program test_shaw_reference
  use shaw_column_api
  use iso_fortran_env, only: real64
  implicit none
  type(shaw_column)::c
  real::z(21),temp(21),water(21),rho(21),k(21),zero(21),sand(21),silt(21),clay(21),ae(21),sat(21),b(21)
  real::air,rain,solar
  integer::i,t,h,u
  do i=1,21
    z(i)=real(i-1)*.05
  enddo
  temp=3.;water=.3;rho=1300.;k=1.e-6;zero=0.;sand=.4;silt=.4;clay=.2;ae=-.3;sat=.48;b=4.5
  call shaw_initialize(c,21,z,temp,water,45.25,106.)
  call shaw_set_soil_parameters(c,rho,k,zero,sand,silt,clay,zero,zero,ae,sat,b)
  call shaw_set_vegetation(c,2.,.8,.3,.6)
  call shaw_set_forcing_height(c,c%plthgt(1)+2.)
  c%clouds=.5
  open(newunit=u,file='reference.csv',status='replace')
  do t=1,720
    h=mod(t-1,24)+1
    air=-7.+14.*real(t)/720.+4.*sin(real(h-8)*acos(-1.)/12.)
    solar=max(0.,200.*sin(real(h-6)*acos(-1.)/12.))
    rain=0.
    if(mod(t,47)==0) rain=.002
    call shaw_advance_hour(c,2020,20+(t-1)/24,h,air,.7,2.,solar,rain)
    write(u,'(i0,*(",",es18.9))') t,c%tsdt(1:21),c%vlcdt(1:21),c%vicdt(1:21), &
      c%pcandt,shaw_swe(c),shaw_storage(c),c%flux
  enddo
  close(u)
end program

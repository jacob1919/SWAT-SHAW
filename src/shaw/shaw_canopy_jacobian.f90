! Derivatives of the original CANTK constitutive law at fixed wind/geometry.
! This helper changes the nonlinear Jacobian, not the physical heat flux.
subroutine SHP_CANTK_DERIV(nc,con,tc,zc,dtop,dbot)
  use shaw_common_access, only: constn_g,constn_tka,windv_windc
  implicit none
  integer,intent(in) :: nc
  real,intent(in) :: con(10),tc(11),zc(11)
  real,intent(out) :: dtop(10),dbot(10)
  real :: richardson,derivative,scale
  integer :: i
  dtop=0.; dbot=0.
  do i=1,nc
    ! CANTK clamps the turbulent conductivity to molecular conduction.
    if(con(i)<=constn_tka/(zc(i+1)-zc(i))) cycle
    scale=constn_g*(zc(i+1)-zc(i))/(tc(i)+273.16)/(windv_windc(i)-windv_windc(i+1))**2
    richardson=scale*(tc(i)-tc(i+1))
    ! CANTK bounds transformed stability to [-2,1]. For stable air the
    ! upper limit corresponds to Ri=1/6, before its separate Ri=0.175 cap.
    if(richardson<=-2..or.richardson>=1./6.) cycle
    if(richardson>=0.) then
      ! Conductance is proportional to 1/PHIH = 1-5*Ri.
      derivative=-5.*con(i)/(1.-5.*richardson)
    else
      ! Unstable air: 1/PHIH = sqrt(1-16*Ri).
      derivative=-8.*con(i)/(1.-16.*richardson)
    endif
    dtop(i)=derivative*scale*(tc(i+1)+273.16)/(tc(i)+273.16)
    dbot(i)=-derivative*scale
  enddo
end subroutine SHP_CANTK_DERIV

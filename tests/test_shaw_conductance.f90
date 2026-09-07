! Check analytic derivatives against the untouched constitutive routine.
program test_shaw_conductance
  use shaw_common_access
  implicit none
  real :: tc(11),zc(11),con(10),plus(10),minus(10),top(10),bot(10),perturbed(11)
  real :: cases(5),scale,finite_difference,epsilon,max_error,error
  integer :: k,j,i,nc
  windv_zero=1.368820377394466e-5; windv_zh=.001199395585807384
  windv_zmsub=.006; windv_zhsub=.0012; windv_zersub=0.
  windv_stable=0.; windv_ustar=.1
  windv_windc=0.; windv_windc(1)=.91836309536; windv_windc(2)=.91633331436
  zc=0.; zc(2)=.02; tc=13.6253
  cases=[-3.,-.5,.05,.16,.18]
  epsilon=1.e-8; max_error=0.; nc=1
  do k=1,size(cases)
    scale=constn_g*(zc(2)-zc(1))/(tc(1)+273.16)/(windv_windc(1)-windv_windc(2))**2
    tc(2)=tc(1)-cases(k)/scale
    call check_derivatives()
  enddo
  ! Multiple layers also exercise the interior and bottom conductance paths.
  nc=2; zc(1:3)=[0.,.3,.8]; tc(1:3)=[10.,9.,11.]
  windv_zero=.3; windv_zh=.012; windv_windc(1:3)=[1.,.7,.3]
  call check_derivatives()
  print *, 'PASS: canopy conductance derivatives; maximum scaled difference=',max_error
contains
  subroutine check_derivatives()
    call SHP_CANTK(1,nc,con,tc,zc)
    call SHP_CANTK_DERIV(nc,con,tc,zc,top,bot)
    do i=1,nc
      do j=i,i+1
        perturbed=tc; perturbed(j)=tc(j)+epsilon
        call SHP_CANTK(1,nc,plus,perturbed,zc)
        perturbed=tc; perturbed(j)=tc(j)-epsilon
        call SHP_CANTK(1,nc,minus,perturbed,zc)
        finite_difference=(plus(i)-minus(i))/(2.*epsilon)
        if(j==i) then
          error=abs(finite_difference-top(i))/max(1.,abs(top(i)))
        else
          error=abs(finite_difference-bot(i))/max(1.,abs(bot(i)))
        endif
        max_error=max(max_error,error)
        if(error>1.e-5) error stop 'Canopy conductance derivative mismatch'
      enddo
    enddo
  end subroutine
end program test_shaw_conductance

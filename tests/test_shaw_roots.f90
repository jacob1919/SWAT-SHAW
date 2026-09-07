program test_shaw_roots
  implicit none
  real :: potential(99),conductance(99),density(99),uptake(99),xylem,demand,expected(3)
  potential=0.;conductance=0.;density=0.
  potential(1:3)=[-100.,-10.,-1.];conductance(1:3)=1.;density(1:3)=1.;demand=1.
  ! A one-pass update starting at -50 selects nodes 2,3, then p=-6.
  ! Clipping the newly negative node 2 flow gives uptake 5 for demand 1.
  call SHP_ROOT_PARTITION(3,potential,conductance,density,demand,xylem,uptake)
  if(abs(xylem+2.)>1.e-12.or.any(abs(uptake(1:3)-[0.,0.,1.])>1.e-12)) &
    error stop 'Dry-root active-set counterexample failed'
  potential(1:3)=[-1.,-100.,-10.]
  call SHP_ROOT_PARTITION(3,potential,conductance,density,demand,xylem,uptake)
  if(any(abs(uptake(1:3)-[1.,0.,0.])>1.e-12)) error stop 'Root partition depends on node ordering'
  demand=500.
  call SHP_ROOT_PARTITION(3,potential,conductance,density,demand,xylem,uptake)
  if(abs(sum(uptake)-demand)>1.e-10.or.any(uptake(1:3)<0.)) error stop 'Fully active roots violate supply'
  demand=0.
  call SHP_ROOT_PARTITION(3,potential,conductance,density,demand,xylem,uptake)
  if(any(uptake/=0.)) error stop 'Zero demand withdrew soil water'
  demand=1.;density(1)=0.
  call SHP_ROOT_PARTITION(3,potential,conductance,density,demand,xylem,uptake)
  if(any(abs(uptake(1:3)-[0.,0.,1.])>1.e-12)) error stop 'Root-free node supplied water'
  density(1:3)=1.;conductance(1:3)=[1.e-6,2.e-6,1.e-7];demand=1.e-8
  call SHP_ROOT_PARTITION(3,potential,conductance,density,demand,xylem,uptake)
  if(abs(sum(uptake)-demand)>1.e-20) error stop 'Small hydraulic flux violates supply'
  print *, 'PASS: conservative nonnegative root supply, dry layers, ordering and zero demand'
end program test_shaw_roots

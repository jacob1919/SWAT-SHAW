! Nonnegative root supply for a specified whole-plant transpiration demand.
! Solve sum(g_i * max(m_i - p_xylem, 0)) = demand. Recompute the active
! root set until consistent; a single pass can silently discard negative
! root flows and leave positive extraction greater than transpiration.
subroutine SHP_ROOT_PARTITION(ns,potential,conductance,root_density,demand,xylem,uptake)
  implicit none
  integer,intent(in) :: ns
  real,intent(in) :: potential(99),conductance(99),root_density(99),demand
  real,intent(out) :: xylem,uptake(99)
  logical :: active(99),changed
  real :: total_conductance,weighted_potential
  integer :: i,iteration
  if(ns<1.or.ns>99.or.demand<0.) error stop 'Invalid root partition input'
  active=.false.;uptake=0.;xylem=0.
  do i=1,ns
    active(i)=root_density(i)>0..and.conductance(i)>0.
  enddo
  if(.not.any(active)) then
    if(demand>0.) error stop 'Positive transpiration without conducting roots'
    return
  endif
  if(demand==0.) then
    xylem=maxval(potential(1:ns),mask=active(1:ns))
    return
  endif
  ! Starting with all roots makes each removal monotone: discarding a
  ! negative flow raises xylem potential, so a discarded root cannot return.
  do iteration=1,ns+1
    total_conductance=0.;weighted_potential=0.
    do i=1,ns
      if(.not.active(i)) cycle
      total_conductance=total_conductance+conductance(i)
      weighted_potential=weighted_potential+conductance(i)*potential(i)
    enddo
    if(total_conductance<=0.) error stop 'Root partition lost all conducting roots'
    xylem=(weighted_potential-demand)/total_conductance
    changed=.false.
    do i=1,ns
      if(active(i).and.potential(i)<xylem) then
        active(i)=.false.;changed=.true.
      endif
    enddo
    if(changed) cycle
    do i=1,ns
      if(active(i)) uptake(i)=conductance(i)*max(0.,potential(i)-xylem)
    enddo
    return
  enddo
  error stop 'Root active set did not settle'
end subroutine SHP_ROOT_PARTITION

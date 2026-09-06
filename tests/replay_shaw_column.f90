! Diagnostic replay of a rejected hour. Use only with a matching compiler/layout.
program replay_shaw_column
  use shaw_column_api
  implicit none
  type(shaw_column) :: c,forcing
  integer :: u,stat
  character(32) :: setting
  real :: soil_tolerance,canopy_tolerance,before,budget
  open(newunit=u,file='shaw_failed_column.bin',access='stream',form='unformatted',status='old')
  read(u) c
  close(u)
  c%level=0
  call get_environment_variable('SHAW_REPLAY_VERBOSE',setting,status=stat)
  if(stat==0.and.trim(setting)=='1') c%level(1)=2
  call get_environment_variable('SHAW_REPLAY_TOLERANCE',setting,status=stat)
  if(stat==0) then
    read(setting,*) soil_tolerance,canopy_tolerance
    call shaw_set_solver_tolerance(c,soil_tolerance,canopy_tolerance)
  endif
  forcing=c
  before=shaw_storage(c)
  call shaw_advance_hour(c,forcing%year,forcing%julian,forcing%hour,forcing%tmpday,forcing%humday, &
    forcing%winday,forcing%sunhor,forcing%precip)
  print *, 'Replay accepted: parts, top temperature/liquid/ice',c%flux(319),c%tsdt(1),c%vlcdt(1),c%vicdt(1)
  budget=1000.*(shaw_storage(c)-before-c%precip-c%flux(318)+c%flux(1)-c%flux(2)+ &
    c%flux(20+c%ns-1)+sum(c%flux(120:118+c%ns)))
  print *, 'Hourly residual mm, net ET mm:',budget,-1000.*c%flux(2)
end program

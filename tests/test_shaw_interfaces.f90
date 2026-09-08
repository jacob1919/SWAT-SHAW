program test_shaw_interfaces
  use shaw_column_api
  use shaw_common_access, only: radopt_radiation_slope
  use shaw_legacy_state, only: shaw_load_state
  implicit none
  type(shaw_column) :: c,north,south,flat
  real :: z(3),temp(3),water(3),dn,ds,df,again,wind
  character(32) :: mode
  z=[0.,.1,.2];temp=3.;water=.3
  call shaw_initialize(c,3,z,temp,water,45.,100.)
  call get_command_argument(1,mode)
  select case(trim(mode))
  case('bad_height')
    call shaw_set_vegetation(c,2.,5.,1.,.1)
    call shaw_set_forcing_height(c,5.)
    stop 0
  case('bad_aspect')
    call shaw_set_terrain(c,.5,361.)
    stop 0
  case('bad_wind')
    wind=shaw_wind_at_height(2.,0.,10.)
    stop 0
  end select
  call shaw_set_forcing_height(c,10.)
  call shaw_set_vegetation(c,2.,5.,1.,.1)
  if(c%height/=10.) error stop 'Vegetation changed the forcing measurement height'
  wind=shaw_wind_at_height(3.,10.,20.)
  if(wind<=3.) error stop 'Wind profile direction reversed'
  if(abs(shaw_wind_at_height(wind,20.,10.)-3.)>1.e-12) error stop 'Wind height round trip failed'
  if(shaw_wind_at_height(3.,10.,10.)/=3.) error stop 'Wind identity conversion failed'
  north=c;south=c;flat=c
  call shaw_set_terrain(north,.5,0.)
  call shaw_set_terrain(south,.5,180.)
  call shaw_set_terrain(flat,.5)
  if(flat%slope/=north%slope) error stop 'Missing aspect discarded hydraulic slope'
  call radiation(north,dn)
  call radiation(south,ds)
  if(ds<=dn) error stop 'Winter south slope must receive more direct radiation than north'
  call radiation(flat,df)
  if(df<=dn.or.df>=ds) error stop 'Missing aspect is not horizontal radiation'
  call shaw_set_terrain(c,0.)
  call radiation(c,again)
  if(df/=again) error stop 'Hydraulic slope changed missing-aspect radiation'
  call radiation(north,again)
  if(dn/=again) error stop 'Radiation option leaked between HRUs'
  call shaw_load_state(flat%memory)
  if(radopt_radiation_slope/=0.) error stop 'Missing-aspect option not saved'
  print *, 'PASS: aspect radiation, independent hydraulic slope, forcing height and wind conversion',dn,df,ds
contains
  subroutine radiation(column,direct)
    type(shaw_column),intent(in) :: column
    real,intent(out) :: direct
    real :: diffuse,sunslp,altitude,halfday,declination
    call shaw_load_state(column%memory)
    declination=-.4093
    halfday=acos(-tan(column%alatud)*tan(declination))
    call SHP_SOLAR(direct,diffuse,sunslp,altitude,200.,column%alatud,column%slope,column%aspect, &
      12.,halfday,declination,12,1)
  end subroutine
end program

! Generated typed SHAW driver state; dimensions follow official GOSHAW.
module shaw_column_types
  use shaw_legacy_state
  implicit none
  type :: shaw_column
    type(shaw_snapshot) :: memory
    real :: flux(320) = 0.
    integer :: julian = 0
    integer :: hour = 0
    integer :: year = 0
    integer :: nhrpdt = 0
    real :: wwdt = 0
    real :: dtime = 0
    integer :: inital = 0
    integer :: nc = 0
    integer :: nsp = 0
    integer :: nr = 0
    integer :: ns = 0
    real :: toler = 0
    integer :: level(6) = 0
    integer :: mzcinp = 0
    integer :: nrchang = 0
    integer :: inph2o = 0
    integer :: mwatrxt = 0
    integer :: lvlout(20) = 0
    integer :: ivlcbc = 0
    integer :: itmpbc = 0
    real :: tsavg = 0
    integer :: nplant = 0
    real :: plthgt(8) = 0
    real :: pltwgt(8) = 0
    real :: pltlai(8) = 0
    real :: rootdp(8) = 0
    real :: dchar(8) = 0
    real :: tccrit(8) = 0
    real :: rstom0(8) = 0
    real :: rstexp(8) = 0
    real :: pleaf0(8) = 0
    real :: rleaf0(8) = 0
    real :: rroot0(8) = 0
    real :: pcandt(8) = 0
    real :: canalb(8) = 0
    real :: canma = 0
    real :: canmb = 0
    real :: wcmax = 0
    real :: pintrcp(8) = 0
    real :: xangle(8) = 0
    real :: clumpng(8) = 0
    integer :: itype(8) = 0
    integer :: istomate = 0
    real :: stomate(8,10) = 0
    real :: zc(11) = 0
    real :: tcdt(11) = 0
    real :: tlcdt(8,10) = 0
    real :: vapcdt(11) = 0
    real :: wcandt(10) = 0
    real :: zsp(200) = 0
    real :: dzsp(200) = 0
    real :: rhosp(200) = 0
    real :: tspdt(200) = 0
    real :: dlwdt(200) = 0
    integer :: icespt(200) = 0
    real :: wlag(11) = 0
    real :: store = 0
    real :: snowex = 0
    integer :: isnotmp = 0
    real :: snotmp = 0
    real :: zr(10) = 0
    real :: rhor(10) = 0
    real :: trdt(10) = 0
    real :: vaprdt(10) = 0
    real :: gmcdt(10) = 0
    real :: gmcmax = 0
    real :: zrthik = 0
    real :: rload = 0
    real :: cover = 0
    real :: albres = 0
    real :: rescof = 0
    real :: restkb = 0
    real :: dirres = 0
    real :: zs(99) = 0
    real :: tsdt(99) = 0
    real :: vlcdt(99) = 0
    real :: vicdt(99) = 0
    real :: matdt(99) = 0
    real :: concdt(10,99) = 0
    integer :: icesdt(99) = 0
    real :: saltdt(10,99) = 0
    real :: albdry = 0
    real :: albexp = 0
    real :: dgrade(10) = 0
    real :: sltdif(10) = 0
    real :: asalt(99) = 0
    real :: disper(99) = 0
    real :: zmsrf = 0
    real :: zhsrf = 0
    real :: zersrf = 0
    real :: zmsp = 0
    real :: zhsp = 0
    real :: height = 0
    real :: pond = 0
    real :: pondmx = 0
    real :: alatud = 0
    real :: slope = 0
    real :: aspect = 0
    real :: hrnoon = 0
    real :: clouds = 0
    real :: declin = 0
    real :: hafday = 0
    real :: sunhor = 0
    real :: tmpday = 0
    real :: winday = 0
    real :: humday = 0
    real :: precip = 0
    real :: snoden = 0
    real :: soitmp = 0
    real :: vlcday = 0
    real :: soilxt(99) = 0
  end type
contains
  subroutine shaw_call(c)
    use shaw_common_access, only: result_result
    type(shaw_column), intent(inout) :: c
    call shaw_load_state(c%memory)
    call SHP_GOSHAW( &
      c%julian, &
      c%hour, &
      c%year, &
      c%nhrpdt, &
      c%wwdt, &
      c%dtime, &
      c%inital, &
      c%nc, &
      c%nsp, &
      c%nr, &
      c%ns, &
      c%toler, &
      c%level, &
      c%mzcinp, &
      c%nrchang, &
      c%inph2o, &
      c%mwatrxt, &
      c%lvlout, &
      c%ivlcbc, &
      c%itmpbc, &
      c%tsavg, &
      c%nplant, &
      c%plthgt, &
      c%pltwgt, &
      c%pltlai, &
      c%rootdp, &
      c%dchar, &
      c%tccrit, &
      c%rstom0, &
      c%rstexp, &
      c%pleaf0, &
      c%rleaf0, &
      c%rroot0, &
      c%pcandt, &
      c%canalb, &
      c%canma, &
      c%canmb, &
      c%wcmax, &
      c%pintrcp, &
      c%xangle, &
      c%clumpng, &
      c%itype, &
      c%istomate, &
      c%stomate, &
      c%zc, &
      c%tcdt, &
      c%tlcdt, &
      c%vapcdt, &
      c%wcandt, &
      c%zsp, &
      c%dzsp, &
      c%rhosp, &
      c%tspdt, &
      c%dlwdt, &
      c%icespt, &
      c%wlag, &
      c%store, &
      c%snowex, &
      c%isnotmp, &
      c%snotmp, &
      c%zr, &
      c%rhor, &
      c%trdt, &
      c%vaprdt, &
      c%gmcdt, &
      c%gmcmax, &
      c%zrthik, &
      c%rload, &
      c%cover, &
      c%albres, &
      c%rescof, &
      c%restkb, &
      c%dirres, &
      c%zs, &
      c%tsdt, &
      c%vlcdt, &
      c%vicdt, &
      c%matdt, &
      c%concdt, &
      c%icesdt, &
      c%saltdt, &
      c%albdry, &
      c%albexp, &
      c%dgrade, &
      c%sltdif, &
      c%asalt, &
      c%disper, &
      c%zmsrf, &
      c%zhsrf, &
      c%zersrf, &
      c%zmsp, &
      c%zhsp, &
      c%height, &
      c%pond, &
      c%pondmx, &
      c%alatud, &
      c%slope, &
      c%aspect, &
      c%hrnoon, &
      c%clouds, &
      c%declin, &
      c%hafday, &
      c%sunhor, &
      c%tmpday, &
      c%winday, &
      c%humday, &
      c%precip, &
      c%snoden, &
      c%soitmp, &
      c%vlcday, &
      c%soilxt)
    c%flux = result_result
    c%inital = 1
    call shaw_save_state(c%memory)
  end subroutine
end module shaw_column_types

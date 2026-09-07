! Generated serial COMMON/SAVE context. No concurrent SHAW calls.
module shaw_legacy_state
  use iso_fortran_env, only: int32
  implicit none
  integer, parameter :: shaw_state_words = 20700
  type :: shaw_snapshot
    integer(int32) :: words(shaw_state_words) = 0
  end type
contains
  subroutine shaw_load_state(state)
    type(shaw_snapshot), intent(in) :: state
    integer(int32) :: raw_timewt(6)
    common /SHP_TIMEWT/ raw_timewt
    save /SHP_TIMEWT/
    integer(int32) :: raw_constn(60)
    common /SHP_CONSTN/ raw_constn
    save /SHP_CONSTN/
    integer(int32) :: raw_slparm(5942)
    common /SHP_SLPARM/ raw_slparm
    save /SHP_SLPARM/
    integer(int32) :: raw_matrix(5600)
    common /SHP_MATRIX/ raw_matrix
    save /SHP_MATRIX/
    integer(int32) :: raw_windv(64)
    common /SHP_WINDV/ raw_windv
    save /SHP_WINDV/
    integer(int32) :: raw_sv_goshaw(3)
    common /SHP_SV_GOSHAW/ raw_sv_goshaw
    save /SHP_SV_GOSHAW/
    integer(int32) :: raw_swrcoe(10)
    common /SHP_SWRCOE/ raw_swrcoe
    save /SHP_SWRCOE/
    integer(int32) :: raw_lwrcof(14)
    common /SHP_LWRCOF/ raw_lwrcof
    save /SHP_LWRCOF/
    integer(int32) :: raw_rsparm(8)
    common /SHP_RSPARM/ raw_rsparm
    save /SHP_RSPARM/
    integer(int32) :: raw_spprop(18)
    common /SHP_SPPROP/ raw_spprop
    save /SHP_SPPROP/
    integer(int32) :: raw_spwatr(18)
    common /SHP_SPWATR/ raw_spwatr
    save /SHP_SPWATR/
    integer(int32) :: raw_metasp(12)
    common /SHP_METASP/ raw_metasp
    save /SHP_METASP/
    integer(int32) :: raw_clayrs(3704)
    common /SHP_CLAYRS/ raw_clayrs
    save /SHP_CLAYRS/
    integer(int32) :: raw_writeit(170)
    common /SHP_WRITEIT/ raw_writeit
    save /SHP_WRITEIT/
    integer(int32) :: raw_sv_canopy(362)
    common /SHP_SV_CANOPY/ raw_sv_canopy
    save /SHP_SV_CANOPY/
    integer(int32) :: raw_sv_canlayzc(21)
    common /SHP_SV_CANLAYZC/ raw_sv_canlayzc
    save /SHP_SV_CANLAYZC/
    integer(int32) :: raw_radcan(432)
    common /SHP_RADCAN/ raw_radcan
    save /SHP_RADCAN/
    integer(int32) :: raw_radres(40)
    common /SHP_RADRES/ raw_radres
    save /SHP_RADRES/
    integer(int32) :: raw_canlwr(160)
    common /SHP_CANLWR/ raw_canlwr
    save /SHP_CANLWR/
    integer(int32) :: raw_sv_atstab(12)
    common /SHP_SV_ATSTAB/ raw_sv_atstab
    save /SHP_SV_ATSTAB/
    integer(int32) :: raw_sv_leaft(504)
    common /SHP_SV_LEAFT/ raw_sv_leaft
    save /SHP_SV_LEAFT/
    integer(int32) :: raw_sv_cantk(2)
    common /SHP_SV_CANTK/ raw_sv_cantk
    save /SHP_SV_CANTK/
    integer(int32) :: raw_sv_ebsnow(1200)
    common /SHP_SV_EBSNOW/ raw_sv_ebsnow
    save /SHP_SV_EBSNOW/
    integer(int32) :: raw_residu(40)
    common /SHP_RESIDU/ raw_residu
    save /SHP_RESIDU/
    integer(int32) :: raw_sv_ebres(20)
    common /SHP_SV_EBRES/ raw_sv_ebres
    save /SHP_SV_EBRES/
    integer(int32) :: raw_spheat(198)
    common /SHP_SPHEAT/ raw_spheat
    save /SHP_SPHEAT/
    integer(int32) :: raw_sv_ebsoil(792)
    common /SHP_SV_EBSOIL/ raw_sv_ebsoil
    save /SHP_SV_EBSOIL/
    integer(int32) :: raw_sv_soiltk(31)
    common /SHP_SV_SOILTK/ raw_sv_soiltk
    save /SHP_SV_SOILTK/
    integer(int32) :: raw_sv_wbsoil(396)
    common /SHP_SV_WBSOIL/ raw_sv_wbsoil
    save /SHP_SV_WBSOIL/
    integer(int32) :: raw_sv_sumdt(16)
    common /SHP_SV_SUMDT/ raw_sv_sumdt
    save /SHP_SV_SUMDT/
    integer(int32) :: raw_sv_snomlt(2)
    common /SHP_SV_SNOMLT/ raw_sv_snomlt
    save /SHP_SV_SNOMLT/
    integer(int32) :: raw_sv_rainsl(200)
    common /SHP_SV_RAINSL/ raw_sv_rainsl
    save /SHP_SV_RAINSL/
    integer(int32) :: raw_result(640)
    common /SHP_RESULT/ raw_result
    save /SHP_RESULT/
    integer(int32) :: raw_options(3)
    common /SHP_OPTIONS/ raw_options
    save /SHP_OPTIONS/
    raw_timewt = state%words(1:6)
    raw_constn = state%words(7:66)
    raw_slparm = state%words(67:6008)
    raw_matrix = state%words(6009:11608)
    raw_windv = state%words(11609:11672)
    raw_sv_goshaw = state%words(11673:11675)
    raw_swrcoe = state%words(11676:11685)
    raw_lwrcof = state%words(11686:11699)
    raw_rsparm = state%words(11700:11707)
    raw_spprop = state%words(11708:11725)
    raw_spwatr = state%words(11726:11743)
    raw_metasp = state%words(11744:11755)
    raw_clayrs = state%words(11756:15459)
    raw_writeit = state%words(15460:15629)
    raw_sv_canopy = state%words(15630:15991)
    raw_sv_canlayzc = state%words(15992:16012)
    raw_radcan = state%words(16013:16444)
    raw_radres = state%words(16445:16484)
    raw_canlwr = state%words(16485:16644)
    raw_sv_atstab = state%words(16645:16656)
    raw_sv_leaft = state%words(16657:17160)
    raw_sv_cantk = state%words(17161:17162)
    raw_sv_ebsnow = state%words(17163:18362)
    raw_residu = state%words(18363:18402)
    raw_sv_ebres = state%words(18403:18422)
    raw_spheat = state%words(18423:18620)
    raw_sv_ebsoil = state%words(18621:19412)
    raw_sv_soiltk = state%words(19413:19443)
    raw_sv_wbsoil = state%words(19444:19839)
    raw_sv_sumdt = state%words(19840:19855)
    raw_sv_snomlt = state%words(19856:19857)
    raw_sv_rainsl = state%words(19858:20057)
    raw_result = state%words(20058:20697)
    raw_options = state%words(20698:20700)
  end subroutine
  subroutine shaw_save_state(state)
    type(shaw_snapshot), intent(out) :: state
    integer(int32) :: raw_timewt(6)
    common /SHP_TIMEWT/ raw_timewt
    save /SHP_TIMEWT/
    integer(int32) :: raw_constn(60)
    common /SHP_CONSTN/ raw_constn
    save /SHP_CONSTN/
    integer(int32) :: raw_slparm(5942)
    common /SHP_SLPARM/ raw_slparm
    save /SHP_SLPARM/
    integer(int32) :: raw_matrix(5600)
    common /SHP_MATRIX/ raw_matrix
    save /SHP_MATRIX/
    integer(int32) :: raw_windv(64)
    common /SHP_WINDV/ raw_windv
    save /SHP_WINDV/
    integer(int32) :: raw_sv_goshaw(3)
    common /SHP_SV_GOSHAW/ raw_sv_goshaw
    save /SHP_SV_GOSHAW/
    integer(int32) :: raw_swrcoe(10)
    common /SHP_SWRCOE/ raw_swrcoe
    save /SHP_SWRCOE/
    integer(int32) :: raw_lwrcof(14)
    common /SHP_LWRCOF/ raw_lwrcof
    save /SHP_LWRCOF/
    integer(int32) :: raw_rsparm(8)
    common /SHP_RSPARM/ raw_rsparm
    save /SHP_RSPARM/
    integer(int32) :: raw_spprop(18)
    common /SHP_SPPROP/ raw_spprop
    save /SHP_SPPROP/
    integer(int32) :: raw_spwatr(18)
    common /SHP_SPWATR/ raw_spwatr
    save /SHP_SPWATR/
    integer(int32) :: raw_metasp(12)
    common /SHP_METASP/ raw_metasp
    save /SHP_METASP/
    integer(int32) :: raw_clayrs(3704)
    common /SHP_CLAYRS/ raw_clayrs
    save /SHP_CLAYRS/
    integer(int32) :: raw_writeit(170)
    common /SHP_WRITEIT/ raw_writeit
    save /SHP_WRITEIT/
    integer(int32) :: raw_sv_canopy(362)
    common /SHP_SV_CANOPY/ raw_sv_canopy
    save /SHP_SV_CANOPY/
    integer(int32) :: raw_sv_canlayzc(21)
    common /SHP_SV_CANLAYZC/ raw_sv_canlayzc
    save /SHP_SV_CANLAYZC/
    integer(int32) :: raw_radcan(432)
    common /SHP_RADCAN/ raw_radcan
    save /SHP_RADCAN/
    integer(int32) :: raw_radres(40)
    common /SHP_RADRES/ raw_radres
    save /SHP_RADRES/
    integer(int32) :: raw_canlwr(160)
    common /SHP_CANLWR/ raw_canlwr
    save /SHP_CANLWR/
    integer(int32) :: raw_sv_atstab(12)
    common /SHP_SV_ATSTAB/ raw_sv_atstab
    save /SHP_SV_ATSTAB/
    integer(int32) :: raw_sv_leaft(504)
    common /SHP_SV_LEAFT/ raw_sv_leaft
    save /SHP_SV_LEAFT/
    integer(int32) :: raw_sv_cantk(2)
    common /SHP_SV_CANTK/ raw_sv_cantk
    save /SHP_SV_CANTK/
    integer(int32) :: raw_sv_ebsnow(1200)
    common /SHP_SV_EBSNOW/ raw_sv_ebsnow
    save /SHP_SV_EBSNOW/
    integer(int32) :: raw_residu(40)
    common /SHP_RESIDU/ raw_residu
    save /SHP_RESIDU/
    integer(int32) :: raw_sv_ebres(20)
    common /SHP_SV_EBRES/ raw_sv_ebres
    save /SHP_SV_EBRES/
    integer(int32) :: raw_spheat(198)
    common /SHP_SPHEAT/ raw_spheat
    save /SHP_SPHEAT/
    integer(int32) :: raw_sv_ebsoil(792)
    common /SHP_SV_EBSOIL/ raw_sv_ebsoil
    save /SHP_SV_EBSOIL/
    integer(int32) :: raw_sv_soiltk(31)
    common /SHP_SV_SOILTK/ raw_sv_soiltk
    save /SHP_SV_SOILTK/
    integer(int32) :: raw_sv_wbsoil(396)
    common /SHP_SV_WBSOIL/ raw_sv_wbsoil
    save /SHP_SV_WBSOIL/
    integer(int32) :: raw_sv_sumdt(16)
    common /SHP_SV_SUMDT/ raw_sv_sumdt
    save /SHP_SV_SUMDT/
    integer(int32) :: raw_sv_snomlt(2)
    common /SHP_SV_SNOMLT/ raw_sv_snomlt
    save /SHP_SV_SNOMLT/
    integer(int32) :: raw_sv_rainsl(200)
    common /SHP_SV_RAINSL/ raw_sv_rainsl
    save /SHP_SV_RAINSL/
    integer(int32) :: raw_result(640)
    common /SHP_RESULT/ raw_result
    save /SHP_RESULT/
    integer(int32) :: raw_options(3)
    common /SHP_OPTIONS/ raw_options
    save /SHP_OPTIONS/
    state%words(1:6) = raw_timewt
    state%words(7:66) = raw_constn
    state%words(67:6008) = raw_slparm
    state%words(6009:11608) = raw_matrix
    state%words(11609:11672) = raw_windv
    state%words(11673:11675) = raw_sv_goshaw
    state%words(11676:11685) = raw_swrcoe
    state%words(11686:11699) = raw_lwrcof
    state%words(11700:11707) = raw_rsparm
    state%words(11708:11725) = raw_spprop
    state%words(11726:11743) = raw_spwatr
    state%words(11744:11755) = raw_metasp
    state%words(11756:15459) = raw_clayrs
    state%words(15460:15629) = raw_writeit
    state%words(15630:15991) = raw_sv_canopy
    state%words(15992:16012) = raw_sv_canlayzc
    state%words(16013:16444) = raw_radcan
    state%words(16445:16484) = raw_radres
    state%words(16485:16644) = raw_canlwr
    state%words(16645:16656) = raw_sv_atstab
    state%words(16657:17160) = raw_sv_leaft
    state%words(17161:17162) = raw_sv_cantk
    state%words(17163:18362) = raw_sv_ebsnow
    state%words(18363:18402) = raw_residu
    state%words(18403:18422) = raw_sv_ebres
    state%words(18423:18620) = raw_spheat
    state%words(18621:19412) = raw_sv_ebsoil
    state%words(19413:19443) = raw_sv_soiltk
    state%words(19444:19839) = raw_sv_wbsoil
    state%words(19840:19855) = raw_sv_sumdt
    state%words(19856:19857) = raw_sv_snomlt
    state%words(19858:20057) = raw_sv_rainsl
    state%words(20058:20697) = raw_result
    state%words(20698:20700) = raw_options
  end subroutine
end module shaw_legacy_state

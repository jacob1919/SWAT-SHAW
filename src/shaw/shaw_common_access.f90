! Generated typed access to the same serial legacy storage.
module shaw_common_access
  implicit none
  real :: timewt_wt
  real :: timewt_wdt
  real :: timewt_dt
  common /SHP_TIMEWT/ &
    timewt_wt, &
    timewt_wdt, &
    timewt_dt
  save /SHP_TIMEWT/
  real :: constn_lf
  real :: constn_lv
  real :: constn_ls
  real :: constn_g
  real :: constn_ugas
  real :: constn_rhol
  real :: constn_rhoi
  real :: constn_rhom
  real :: constn_rhoom
  real :: constn_rhoa
  real :: constn_cl
  real :: constn_ci
  real :: constn_cm
  real :: constn_com
  real :: constn_ca
  real :: constn_cv
  real :: constn_cr
  real :: constn_vonkrm
  real :: constn_vdiff
  real :: constn_presur
  real :: constn_p0
  real :: constn_tkl
  real :: constn_tki
  real :: constn_tka
  real :: constn_tkr
  real :: constn_tkro
  real :: constn_tksa
  real :: constn_tksi
  real :: constn_tkcl
  real :: constn_tkom
  common /SHP_CONSTN/ &
    constn_lf, &
    constn_lv, &
    constn_ls, &
    constn_g, &
    constn_ugas, &
    constn_rhol, &
    constn_rhoi, &
    constn_rhom, &
    constn_rhoom, &
    constn_rhoa, &
    constn_cl, &
    constn_ci, &
    constn_cm, &
    constn_com, &
    constn_ca, &
    constn_cv, &
    constn_cr, &
    constn_vonkrm, &
    constn_vdiff, &
    constn_presur, &
    constn_p0, &
    constn_tkl, &
    constn_tki, &
    constn_tka, &
    constn_tkr, &
    constn_tkro, &
    constn_tksa, &
    constn_tksi, &
    constn_tkcl, &
    constn_tkom
  save /SHP_CONSTN/
  real :: slparm_rhob(99)
  real :: slparm_satk(99)
  real :: slparm_satklat(99)
  real :: slparm_soilwrc(99,10)
  integer :: slparm_nsalt
  real :: slparm_saltkq(10,99)
  real :: slparm_vapcof(99)
  real :: slparm_vapexp(99)
  real :: slparm_rock(99)
  real :: slparm_sand(99)
  real :: slparm_silt(99)
  real :: slparm_clay(99)
  real :: slparm_om(99)
  integer :: slparm_iwrc
  common /SHP_SLPARM/ &
    slparm_rhob, &
    slparm_satk, &
    slparm_satklat, &
    slparm_soilwrc, &
    slparm_nsalt, &
    slparm_saltkq, &
    slparm_vapcof, &
    slparm_vapexp, &
    slparm_rock, &
    slparm_sand, &
    slparm_silt, &
    slparm_clay, &
    slparm_om, &
    slparm_iwrc
  save /SHP_SLPARM/
  real :: matrix_a1(350)
  real :: matrix_b1(350)
  real :: matrix_c1(350)
  real :: matrix_d1(350)
  real :: matrix_a2(350)
  real :: matrix_b2(350)
  real :: matrix_c2(350)
  real :: matrix_d2(350)
  common /SHP_MATRIX/ &
    matrix_a1, &
    matrix_b1, &
    matrix_c1, &
    matrix_d1, &
    matrix_a2, &
    matrix_b2, &
    matrix_c2, &
    matrix_d2
  save /SHP_MATRIX/
  real :: windv_zh
  real :: windv_zm
  real :: windv_zero
  real :: windv_ustar
  real :: windv_stable
  real :: windv_conrh
  real :: windv_conrv
  real :: windv_zhlog
  real :: windv_zmsub
  real :: windv_zhsub
  real :: windv_zersub
  real :: windv_windc(11)
  real :: windv_windr(10)
  common /SHP_WINDV/ &
    windv_zh, &
    windv_zm, &
    windv_zero, &
    windv_ustar, &
    windv_stable, &
    windv_conrh, &
    windv_conrv, &
    windv_zhlog, &
    windv_zmsub, &
    windv_zhsub, &
    windv_zersub, &
    windv_windc, &
    windv_windr
  save /SHP_WINDV/
  integer :: sv_goshaw_nprint
  integer :: sv_goshaw_maxstp
  integer :: sv_goshaw_minstp
  common /SHP_SV_GOSHAW/ &
    sv_goshaw_nprint, &
    sv_goshaw_maxstp, &
    sv_goshaw_minstp
  save /SHP_SV_GOSHAW/
  real :: swrcoe_solcon
  real :: swrcoe_difatm
  real :: swrcoe_difres
  real :: swrcoe_snocof
  real :: swrcoe_snoexp
  common /SHP_SWRCOE/ &
    swrcoe_solcon, &
    swrcoe_difatm, &
    swrcoe_difres, &
    swrcoe_snocof, &
    swrcoe_snoexp
  save /SHP_SWRCOE/
  real :: lwrcof_stefan
  real :: lwrcof_ematm1
  real :: lwrcof_ematm2
  real :: lwrcof_emitc
  real :: lwrcof_emitr
  real :: lwrcof_emitsp
  real :: lwrcof_emits
  common /SHP_LWRCOF/ &
    lwrcof_stefan, &
    lwrcof_ematm1, &
    lwrcof_ematm2, &
    lwrcof_emitc, &
    lwrcof_emitr, &
    lwrcof_emitsp, &
    lwrcof_emits
  save /SHP_LWRCOF/
  real :: rsparm_resma
  real :: rsparm_resmb
  real :: rsparm_resmc
  real :: rsparm_restka
  common /SHP_RSPARM/ &
    rsparm_resma, &
    rsparm_resmb, &
    rsparm_resmc, &
    rsparm_restka
  save /SHP_RSPARM/
  real :: spprop_g1
  real :: spprop_g2
  real :: spprop_g3
  real :: spprop_extsp
  real :: spprop_tkspa
  real :: spprop_tkspb
  real :: spprop_tkspex
  real :: spprop_vdifsp
  real :: spprop_vapspx
  common /SHP_SPPROP/ &
    spprop_g1, &
    spprop_g2, &
    spprop_g3, &
    spprop_extsp, &
    spprop_tkspa, &
    spprop_tkspb, &
    spprop_tkspex, &
    spprop_vdifsp, &
    spprop_vapspx
  save /SHP_SPPROP/
  real :: spwatr_clag1
  real :: spwatr_clag2
  real :: spwatr_clag3
  real :: spwatr_clag4
  real :: spwatr_plwmax
  real :: spwatr_plwden
  real :: spwatr_plwhc
  real :: spwatr_thick
  real :: spwatr_cthick
  common /SHP_SPWATR/ &
    spwatr_clag1, &
    spwatr_clag2, &
    spwatr_clag3, &
    spwatr_clag4, &
    spwatr_plwmax, &
    spwatr_plwden, &
    spwatr_plwhc, &
    spwatr_thick, &
    spwatr_cthick
  save /SHP_SPWATR/
  real :: metasp_cmet1
  real :: metasp_cmet2
  real :: metasp_cmet3
  real :: metasp_cmet4
  real :: metasp_cmet5
  real :: metasp_snomax
  common /SHP_METASP/ &
    metasp_cmet1, &
    metasp_cmet2, &
    metasp_cmet3, &
    metasp_cmet4, &
    metasp_cmet5, &
    metasp_snomax
  save /SHP_METASP/
  real :: clayrs_plantz(8)
  real :: clayrs_drycan(8,10)
  real :: clayrs_canlai(8,10)
  real :: clayrs_totlai(8)
  integer :: clayrs_ievap(8)
  real :: clayrs_rleaf(8,10)
  real :: clayrs_rroot(8,99)
  real :: clayrs_rootdn(8,99)
  real :: clayrs_totrot(8)
  common /SHP_CLAYRS/ &
    clayrs_plantz, &
    clayrs_drycan, &
    clayrs_canlai, &
    clayrs_totlai, &
    clayrs_ievap, &
    clayrs_rleaf, &
    clayrs_rroot, &
    clayrs_rootdn, &
    clayrs_totrot
  save /SHP_CLAYRS/
  real :: writeit_hflux1
  real :: writeit_rh
  real :: writeit_hnc
  real :: writeit_xlenc
  real :: writeit_contk
  real :: writeit_tleaf(8,10)
  common /SHP_WRITEIT/ &
    writeit_hflux1, &
    writeit_rh, &
    writeit_hnc, &
    writeit_xlenc, &
    writeit_contk, &
    writeit_tleaf
  save /SHP_WRITEIT/
  real :: sv_canopy_zzc(11)
  real :: sv_canopy_dzcan(10)
  real :: sv_canopy_ddrycan(8,10)
  real :: sv_canopy_ccanlai(8,10)
  common /SHP_SV_CANOPY/ &
    sv_canopy_zzc, &
    sv_canopy_dzcan, &
    sv_canopy_ddrycan, &
    sv_canopy_ccanlai
  save /SHP_SV_CANOPY/
  integer :: sv_canlayzc_mzc
  real :: sv_canlayzc_zmid(10)
  common /SHP_SV_CANLAYZC/ &
    sv_canlayzc_mzc, &
    sv_canlayzc_zmid
  save /SHP_SV_CANLAYZC/
  real :: radcan_tdircc(10)
  real :: radcan_tdiffc(10)
  real :: radcan_dirkl(9,10)
  real :: radcan_difkl(9,10)
  real :: radcan_fbdu(8)
  real :: radcan_fddu(8)
  common /SHP_RADCAN/ &
    radcan_tdircc, &
    radcan_tdiffc, &
    radcan_dirkl, &
    radcan_difkl, &
    radcan_fbdu, &
    radcan_fddu
  save /SHP_RADCAN/
  real :: radres_tdirec(10)
  real :: radres_tdiffu(10)
  common /SHP_RADRES/ &
    radres_tdirec, &
    radres_tdiffu
  save /SHP_RADRES/
  real :: canlwr_tlclwr(8,10)
  common /SHP_CANLWR/ &
    canlwr_tlclwr
  save /SHP_CANLWR/
  real :: sv_atstab_tmpair
  real :: sv_atstab_vapair
  real :: sv_atstab_zmlog
  real :: sv_atstab_zclog
  real :: sv_atstab_psim
  real :: sv_atstab_psih
  common /SHP_SV_ATSTAB/ &
    sv_atstab_tmpair, &
    sv_atstab_vapair, &
    sv_atstab_zmlog, &
    sv_atstab_zclog, &
    sv_atstab_psim, &
    sv_atstab_psih
  save /SHP_SV_ATSTAB/
  integer :: sv_leaft_init(8)
  real :: sv_leaft_pxylem(8)
  real :: sv_leaft_rhcan(8,10)
  real :: sv_leaft_rvcan(8,10)
  real :: sv_leaft_etcan(8,10)
  common /SHP_SV_LEAFT/ &
    sv_leaft_init, &
    sv_leaft_pxylem, &
    sv_leaft_rhcan, &
    sv_leaft_rvcan, &
    sv_leaft_etcan
  save /SHP_SV_LEAFT/
  real :: sv_cantk_zmlog
  common /SHP_SV_CANTK/ &
    sv_cantk_zmlog
  save /SHP_SV_CANTK/
  real :: sv_ebsnow_qvspt(200)
  real :: sv_ebsnow_con(200)
  real :: sv_ebsnow_cspt(200)
  common /SHP_SV_EBSNOW/ &
    sv_ebsnow_qvspt, &
    sv_ebsnow_con, &
    sv_ebsnow_cspt
  save /SHP_SV_EBSNOW/
  real :: residu_evap(10)
  real :: residu_evapk(10)
  common /SHP_RESIDU/ &
    residu_evap, &
    residu_evapk
  save /SHP_RESIDU/
  real :: sv_ebres_crest(10)
  common /SHP_SV_EBRES/ &
    sv_ebres_crest
  save /SHP_SV_EBRES/
  real :: spheat_cs(99)
  common /SHP_SPHEAT/ &
    spheat_cs
  save /SHP_SPHEAT/
  real :: sv_ebsoil_qsvt(99)
  real :: sv_ebsoil_qslt(99)
  real :: sv_ebsoil_tkt(99)
  real :: sv_ebsoil_cst(99)
  common /SHP_SV_EBSOIL/ &
    sv_ebsoil_qsvt, &
    sv_ebsoil_qslt, &
    sv_ebsoil_tkt, &
    sv_ebsoil_cst
  save /SHP_SV_EBSOIL/
  integer :: sv_soiltk_ifirst
  real :: sv_soiltk_wfaird
  real :: sv_soiltk_wfrod
  real :: sv_soiltk_wfsad
  real :: sv_soiltk_wfsid
  real :: sv_soiltk_wfcld
  real :: sv_soiltk_wfomd
  real :: sv_soiltk_wficed
  real :: sv_soiltk_tkma
  real :: sv_soiltk_wfl
  real :: sv_soiltk_wfro
  real :: sv_soiltk_wfsa
  real :: sv_soiltk_wfsi
  real :: sv_soiltk_wfcl
  real :: sv_soiltk_wfom
  real :: sv_soiltk_wfice
  common /SHP_SV_SOILTK/ &
    sv_soiltk_ifirst, &
    sv_soiltk_wfaird, &
    sv_soiltk_wfrod, &
    sv_soiltk_wfsad, &
    sv_soiltk_wfsid, &
    sv_soiltk_wfcld, &
    sv_soiltk_wfomd, &
    sv_soiltk_wficed, &
    sv_soiltk_tkma, &
    sv_soiltk_wfl, &
    sv_soiltk_wfro, &
    sv_soiltk_wfsa, &
    sv_soiltk_wfsi, &
    sv_soiltk_wfcl, &
    sv_soiltk_wfom, &
    sv_soiltk_wfice
  save /SHP_SV_SOILTK/
  real :: sv_wbsoil_qslt(99)
  real :: sv_wbsoil_qsvt(99)
  common /SHP_SV_WBSOIL/ &
    sv_wbsoil_qslt, &
    sv_wbsoil_qsvt
  save /SHP_SV_WBSOIL/
  real :: sv_sumdt_transp(8)
  common /SHP_SV_SUMDT/ &
    sv_sumdt_transp
  save /SHP_SV_SUMDT/
  integer :: sv_snomlt_ifirst
  integer :: sv_snomlt_nlag
  common /SHP_SV_SNOMLT/ &
    sv_snomlt_ifirst, &
    sv_snomlt_nlag
  save /SHP_SV_SNOMLT/
  real :: sv_rainsl_psatk
  real :: sv_rainsl_psat(99)
  common /SHP_SV_RAINSL/ &
    sv_rainsl_psatk, &
    sv_rainsl_psat
  save /SHP_SV_RAINSL/
  real :: result_result(320)
  common /SHP_RESULT/ &
    result_result
  save /SHP_RESULT/
  real :: options_canopy_water_tol
  integer :: options_canopy_jacobian
  common /SHP_OPTIONS/ &
    options_canopy_water_tol, &
    options_canopy_jacobian
  save /SHP_OPTIONS/
end module shaw_common_access

"""Write the Chinese process-comparison report only from complete, consistent runs."""
from pathlib import Path
import argparse
import csv
import datetime as dt
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
MODES = ('official', 'existing_ft', 'shaw')
LABELS = {'official': '原始 SWAT+', 'existing_ft': '既有冻融版', 'shaw': 'SHAW 耦合版'}
PERIODS = {'full_simulation': '完整模拟', 'warmup': '2020 预热', 'evaluation': '评价期'}


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f'Nonfinite report value: {value}')
    return result


def fmt(value, digits=3):
    return f'{number(value):,.{digits}f}'


def table(headers, rows):
    lines = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |']
    lines.extend('| ' + ' | '.join(str(x) for x in row) + ' |' for row in rows)
    return '\n'.join(lines)


def validate(summary, status, annual, daily, run_root=None):
    if summary.get('status') != 'complete' or status.get('status') != 'complete' or status.get('errors'):
        raise ValueError('Report withheld: summary.json and analysis_status.json must both be complete without errors')
    runs = summary['runs']
    if runs != status.get('runs'):
        raise ValueError('Report withheld: summary and analysis status refer to different runs')
    for mode in (*MODES, 'coupling_off'):
        run = runs[mode]
        if run.get('exit_code') != 0 or not run.get('completed_utc') or not run.get('sha256'):
            raise ValueError(f'Report withheld: unsuccessful or incomplete {mode} run')
        if run_root is not None and load_json(run_root / mode / 'run.json') != run:
            raise ValueError(f'Report withheld: {mode} has been rerun since the comparison was generated')
    if runs['shaw']['sha256'] != runs['coupling_off']['sha256']:
        raise ValueError('Report withheld: coupled and coupling-off executable hashes differ')
    for name in ('forcing_parity','transport_compatibility'):
        check=summary[name]
        if check.get('status')!='pass' or check.get('coupled_executable_sha256')!=runs['shaw']['sha256']:
            raise ValueError(f'Report withheld: stale or unsuccessful {name}')
    if not math.isclose(number(summary['total_area_km2']), 15.1818012, abs_tol=1e-7):
        raise ValueError('Unexpected basin area; this report describes the supplied Canadian case')
    if summary['total_hrus'] != 142 or summary['coupled_hrus'] != 123:
        raise ValueError('Unexpected HRU scope; review report assumptions before continuing')
    start = dt.date(2021, 1, 1)
    expected_dates = [str(start + dt.timedelta(days=i)) for i in range(850)]
    if [r['date'] for r in daily] != expected_dates or summary['evaluation_days'] != 850:
        raise ValueError('Incomplete or unexpected daily evaluation period')
    expected_keys = {(m, y) for m in MODES for y in (2021, 2022, 2023)}
    if len(annual) != 9 or {(r['model'], int(r['year'])) for r in annual} != expected_keys:
        raise ValueError('Expected exactly nine model/year rows')
    for row in annual:
        mode, year = row['model'], int(row['year'])
        days = [r for r in daily if int(r['date'][:4]) == year]
        if int(row['days']) != len(days) or row['period_start'] != days[0]['date'] or row['period_end'] != days[-1]['date']:
            raise ValueError(f'Annual/daily period mismatch: {mode}/{year}')
        checks = {'mean_outlet_m3s': sum(number(r[mode + '_outlet_m3s']) for r in days) / len(days),
                  'peak_outlet_m3s': max(number(r[mode + '_outlet_m3s']) for r in days),
                  'max_snowpack_mm': max(number(r[mode + '_snopack_mm']) for r in days)}
        for field in ('et', 'surq_gen', 'perc', 'latq'):
            checks[field + '_mm'] = sum(number(r[mode + '_' + field + '_mm']) for r in days)
        for field, value in checks.items():
            if not math.isclose(number(row[field]), value, rel_tol=1e-10, abs_tol=1e-8):
                raise ValueError(f'Annual/daily value mismatch: {mode}/{year}/{field}')
    for period, days in (('full_simulation', 1216), ('warmup', 366), ('evaluation', 850)):
        budget = summary['water_budget'][period]
        if budget['days'] != days or budget['hru_days'] != days * summary['coupled_hrus']:
            raise ValueError(f'Incomplete water-budget period: {period}')
        if number(budget['max_absolute_hru_daily_residual_mm']) > 0.10001:
            raise ValueError(f'Water-budget acceptance limit exceeded: {period}')


def render_report(summary, annual, daily, kernel, ames, hashes, parity=None, guard=None):
    area = number(summary['total_area_km2'])
    coupled_area = number(summary['coupled_area_ha'])
    fraction = 100 * coupled_area / number(summary['total_area_ha'])
    scope = (f"流域面积 **{area:.7f} km²**（{fmt(summary['total_area_ha'], 5)} ha），"
             f"共有 **{summary['total_hrus']} 个有效 HRU**，其中 **{summary['coupled_hrus']} 个**使用 SHAW，"
             f"面积 {fmt(coupled_area, 5)} ha，占 {fraction:.2f}%。"
             f"其余 {summary['total_hrus'] - summary['coupled_hrus']} 个 HRU 保留原始过程；零面积占位对象不计入统计。"
             f"流量统计使用终端河道 {', '.join(str(x) for x in summary['outlet_channel_ids'])}。")
    annual_rows = []
    reasons={'SHAW coupled':'SHAW 耦合','urban impervious surface':'城市 HRU，保留原始过程',
             'surface water body':'地表水体，保留原始过程','tile drainage':'暗管排水，保留原始过程',
             'septic system':'化粪系统，保留原始过程'}
    scope_table=table(['过程配置','HRU 数','面积（ha）','流域面积占比'],
        [[reasons.get(reason,reason),group['hrus'],fmt(group['area_ha'],5),
          fmt(100*group['area_ha']/number(summary['total_area_ha']),2)+'%']
         for reason,group in summary['scope_groups'].items()])
    for year in (2021, 2022, 2023):
        for mode in MODES:
            r = next(r for r in annual if r['model'] == mode and int(r['year']) == year)
            annual_rows.append([LABELS[mode], str(year) + ('（1–4 月）' if year == 2023 else ''), r['days'],
                fmt(r['mean_outlet_m3s'], 6), fmt(r['et_mm']), fmt(r['surq_gen_mm']),
                fmt(r['perc_mm']), fmt(r['latq_mm']), fmt(r['max_snowpack_mm'])])
    annual_table = table(['模型', '年份', '天数', '平均 Q（m³/s）', 'ET（mm）', '地表产流（mm）',
                          '渗漏（mm）', '侧向流（mm）', '最大 SWE（mm）'], annual_rows)
    peaks = []
    comparison = []
    for mode in MODES:
        values = [number(r[mode + '_outlet_m3s']) for r in daily]
        peak = max(range(len(values)), key=values.__getitem__)
        peaks.append([LABELS[mode], fmt(values[peak], 6), daily[peak]['date']])
        difference = summary['model_differences'].get(mode, {})
        change = difference.get('outlet_mean_change_percent')
        rmse = difference.get('outlet_daily_rmse_vs_official_m3s')
        comparison.append([LABELS[mode], fmt(sum(values) / len(values), 6),
            fmt(sum(values) * 86400 / (area * 1000)),
            '基准' if mode == 'official' else ('基准均流为零' if change is None else fmt(change, 2) + '%'),
            '基准' if mode == 'official' else fmt(rmse, 6)])
    evaluation_table = table(['模型', '评价期平均 Q（m³/s）', '出口累计径流深（mm）',
                               '平均 Q 相对原始版变化', '日 Q 与原始版的 RMSE（m³/s）'], comparison)
    flux_findings=[]
    for field,label in (('et','净蒸散'),('surq_gen','地表产流'),('perc','底部渗漏')):
        original=sum(number(r['official_'+field+'_mm']) for r in daily)
        coupled=sum(number(r['shaw_'+field+'_mm']) for r in daily)
        percent='原始值为零，未计算百分比' if original==0 else f'变化 {100*(coupled/original-1):+.2f}%'
        flux_findings.append(f'- 评价期累计{label}：原始版 {fmt(original)} mm，SHAW 耦合版 {fmt(coupled)} mm（{percent}）。')
    process_findings='\n'.join(flux_findings)
    thermal_table = table(['模型','第二土层平均 T（°C）','最低 T（°C）','最高 T（°C）','面平均 T < 0°C 的天数'],
        [[LABELS[mode],fmt(summary['soil_thermal_response'][mode]['mean_soil_layer2_C']),
          fmt(summary['soil_thermal_response'][mode]['min_soil_layer2_C']),
          fmt(summary['soil_thermal_response'][mode]['max_soil_layer2_C']),
          summary['soil_thermal_response'][mode]['days_basin_mean_layer2_below_zero']] for mode in MODES])
    budget_rows = []
    retry_rows = []
    for key, label in PERIODS.items():
        b = summary['water_budget'][key]
        canopy = (fmt(b['coupled_area_flux_totals_mm']['canopy_air_exchange_mm'], 6)
                  if b.get('canopy_air_exchange_reported') else '未单列')
        budget_rows.append([label, b['days'], fmt(b['max_absolute_hru_daily_residual_mm'], 6),
            fmt(b['coupled_area_cumulative_signed_residual_mm'], 6),
            fmt(b['coupled_area_cumulative_absolute_hru_residual_mm'], 6), canopy])
        retry_rows.append([label, f"{b['hru_days']:,}", f"{b['retried_hru_hours']:,}",
            fmt(b['retried_hru_hours_percent'], 4) + '%', f"{b['hru_days_requiring_retry']:,}", b['max_hour_parts'],
            f"{b['jacobian_retry_hours']:,}"])
    budget_table = table(['时段', '天数', '最大单 HRU 日残差绝对值（mm）',
                           '累计有符号残差（mm）', '累计绝对残差（mm，先逐 HRU 取绝对值）',
                           '累计冠层空气水量交换（mm）'], budget_rows)
    retry_table = table(['时段', 'HRU·日', '发生重试的 HRU·小时', '小时占比', '发生重试的 HRU·日',
                          '最大小时分段数','采用附加导数的 HRU·小时'], retry_rows)
    test_lines = []
    ref = kernel.get('official_reference')
    if ref:
        test_lines.append(f"官方算法参照路径比较 {ref['hours']:,} 小时、{ref['values_compared']:,} 个物理数值，"
                          f"不一致数为 {ref['different_values']:,}，最大绝对差为 {fmt(ref['max_absolute_difference'], 9)}。"
                          '该检查使用无溶质、相同适配器输入和匹配编译精度；不包括官方输入读取器的全面验证。')
    for key, label in (('shaw_column_test', '独立/交替土柱'), ('shaw_canopy_test', '动态冠层')):
        result = kernel.get(key)
        if result:
            test_lines.append(f"{label}检查为 {result['hours']} 小时，最大逐小时水量残差 "
                              f"{fmt(result['max_abs_hourly_residual_mm'], 9)} mm，验收限值为 0.002 mm。")
    reg = summary['regression']
    conductance = kernel.get('shaw_conductance_test')
    if conductance:
        test_lines.append(f"冠层交换系数温度导数与原始函数有限差分比较，最大缩放差 "
                          f"{conductance['max_scaled_derivative_difference']:.6g}，"
                          f"限值 {conductance['acceptance_limit']:.6g}。")
    roots = kernel.get('shaw_root_test')
    if roots and roots.get('status') == 'pass':
        test_lines.append('根系供水检查覆盖干湿土层反例、节点排序、零需求及微小通量；'
                          '每个接受小时另检查根系吸水与蒸腾差不超过 1e-6 mm。')
    test_lines.append(f"加拿大关闭耦合回归：{reg['files_identical_after_banner']} 个文件、"
                      f"{reg['data_rows']:,} 个数据行在构建标题行之后与固定官方版本完全一致。"
                      '本报告要求关闭耦合和启用耦合使用同一可执行文件 SHA256。')
    if ames.get('status') == 'pass':
        test_lines.append(f"另行由固定官方可执行文件生成的 Ames 结果，在 {len(ames['checks'])} 个指定输出文件中"
                          '与关闭耦合版一致。仓库历史 golden 输出本身与该官方版本存在差异；原有 Ames golden CTest '
                          '仍报告失败，不能称整个 CTest 全部通过。')
    if parity and parity.get('status') == 'pass':
        test_lines.append(f"完整流域与单独 HRU 运行的交叉检查：HRU {', '.join(map(str,parity['hrus']))} "
                          f"共 {parity['daily_rows_compared']:,} 个逐日记录、每行 {parity['columns_per_row']} 列完全一致。"
                          '比较包括状态、通量和重试计数；该案例的这些 HRU 没有上游 HRU 来水，因而应当一致。')
    if guard and guard.get('status') == 'pass':
        replay=guard['corrected_replay']
        test_lines.append(f"原生最小步长处保留六处大幅更新保护，越界尝试完整回退。历史捕获的 HRU 19 失败小时"
                          f"重放时用 {replay['parts']} 个分段通过，水量残差 {fmt(replay['water_residual_mm'],9)} mm；"
                          '该重放的水热内核源码与本次相同，详见最小步长保护复查记录。')
    if not kernel:
        test_lines.append('未找到 kernel_checks.json；本报告不新增内核试验通过的断言。')
    run_rows = []
    for mode in (*MODES, 'coupling_off'):
        run = summary['runs'][mode]
        run_rows.append([LABELS.get(mode, '关闭耦合回归'), fmt(run['seconds'], 3),
                         run['completed_utc'], f"`{run['sha256']}`"])
    hash_lines = '\n'.join(f'- `{name}`：`{digest}`' for name, digest in hashes.items())
    checks = '\n\n'.join(test_lines)
    return f"""# 加拿大流域 SWAT+、既有冻融版与 SHAW 耦合版过程对照

三个版本均已完成 2020-01-01 至 2023-04-30 的 1,216 天模拟。**本次结果是未率定的模型过程差异比较，不能证明预测精度提高**；提供的案例未附实测流量、雪水当量或土温序列。以下数值由完整运行产物自动生成。

## 数据与可比范围

{scope}

{scope_table}

逐 HRU 面积、过程配置和选择原因见 [耦合范围 CSV](hru_scope.csv)。若一个 HRU 同时符合多项保留原始过程的条件，表中记录程序最后匹配的原因，每个 HRU 只计一次。

本次重新核对了此前报告的基础口径：旧报告把面积的 ha 数值标为 km²，并将该起止日期的模拟天数写为 1,456；本报告采用输入面积换算后的 15.1818012 km² 和按日历计算的 1,216 天。旧报告文件保留原样。

2020 年的 366 天作为预热，评价期为 **2021-01-01 至 2023-04-30，共 850 天**。2023 年仅含 1–4 月的 120 天，年度累计量不能与完整年度直接比较。该案例代表加拿大季节性冻土环境，不应据此外推多年冻土区。

案例来自用户此前使用的 [SWAT+ 用户组加拿大数据](https://groups.google.com/g/swatplus/c/lnI2RShJmZw)。三个版本采用相同的 79 个输入文件，沿用此前土壤水文组数字 `3 → C` 的修正，并统一日输出设置；输入 SHA256 清单保存在本机 `validation/canada/input_manifest.json`。原始 AWC 数值问题由共同的 SWAT+ 初始化规则处理，仍是参数解释的限制。

逐日降水和气温来自案例输入，短波辐射、相对湿度和风速来自 SWAT+ 气象发生器。耦合时将日降水均匀分配到 24 小时，重建日内温度与短波，湿度和风速日内保持不变，云量暂定 0.5；这些逐小时序列是构造强迫，不能视为逐小时观测。

除了输入哈希，程序还检查了评价期全部 142 个 HRU、850 天的实际日输出：降水、最高/最低/平均气温、短波辐射、湿度和风速在三个版本间按输出精度完全一致，见 [气象一致性记录](forcing_parity.json)。2020 年预热期未打印这些逐日表，该时段由输入文件哈希覆盖。

共同 SWAT+ 基线为 `61c940f40b5da768edc62a30641d9a1fbebc2708`。既有冻融可执行文件还包含冻融之外的代码修改，因此它与原始版的差异不能全部归因于冻融机制。耦合版只移植与产汇流水热有关的 SHAW 过程，不启用 SHAW 溶质或 CO₂ 过程；仍保留 SWAT+ 管理、植被生长和空间汇流框架。部分 HRU 保留原始水热过程，出口结果反映这一混合配置。

## 评价期出口流量

{evaluation_table}

出口累计径流深由日平均流量积分并除以整个流域面积得到；它包含流域汇流后的贡献，不等于 HRU 地表产流。表中的 RMSE 衡量两个模拟序列的差异，不是相对实测的误差，也不是模型优劣排名。

{table(['模型', '评价期最大日平均 Q（m³/s）', '发生日期'], peaks)}

SHAW 耦合版相对原始版的水量分配变化：

{process_findings}

这些差异同时包含冠层、积雪、土壤水热及产流算法的替换效应。尤其是把日雨均匀分为小时输入、由 CN 法转为 SHAW 入渗和地表积水过程，会影响径流与渗漏的分配；本次试验不能把变化全部归为冻融效应。

## 年度过程量

{annual_table}

ET、地表产流、底部渗漏和侧向流为全流域面积平均的时段累计深度；SWE 为该时段最大流域平均积雪水当量。最大日平均 Q 不等于瞬时洪峰。完整降水、降雪和融雪等统计见 [年度 CSV](annual_comparison.csv)，逐日序列见 [逐日 CSV](daily_comparison.csv)。

![出口流量、积雪、蒸散与渗漏过程](process_comparison.png)

[科学绘图 PDF](process_comparison.pdf)

## 冬春过程与季节统计

下图放大各年 1—5 月的出口流量和积雪过程；2023 年仅到 4 月底，5 月留空。各列采用相同纵轴，便于比较幅度。季节累计与峰值见 [季节 CSV](seasonal_comparison.csv)：采用气象季节 DJF/MAM/JJA/SON，12 月归入下一冬季年份；2021 冬季缺少预热期的 2020 年 12 月，2023 春季缺少 5 月，均标为不完整季节。

![冬春出口流量与积雪](winter_spring_comparison.png)

[冬春绘图 PDF](winter_spring_comparison.pdf)

## 土温与土壤冰

{thermal_table}

土温来自三个版本共同输出的 `basin_pw_day.txt: sol_tmp`，源代码均取 `soil(j)%phys(2)%tmp` 后按流域面积汇总，即 **SWAT+ 第二土层温度**，不是地表温度，也不代表全流域统一物理深度。温度低于零的天数按日输出精度判定，指面平均序列过零，不能解释为所有 HRU 的冻结持续天数或冻土面积比例。

![第二土层温度与 SHAW 土壤冰储量](thermal_comparison.png)

[土温与冰储量绘图 PDF](thermal_comparison.pdf)

下半图仅显示 SHAW 耦合域的土壤冰水当量，不含积雪；评价期最大耦合域平均土壤冰储量为 {fmt(summary['water_budget']['evaluation']['max_coupled_area_ice_water_mm'])} mm。当前原始版及既有冻融版运行没有同口径土壤冰输出，因此不构造其冰量曲线。逐日温度及冰量与水文量一同写入逐日 CSV。

## 耦合域水量收支与数值重试

逐 HRU 日账本采用 `储量变化 − 降水 − 外部土壤来水 − 地表来水 − 冠层空气水量交换 + 净蒸散 + 径流 + 底部渗漏 + 侧向流`。冠层空气水量交换是冠层几何变化导致的空气控制体水汽储量变化，独立记为有符号输入，不并入物理蒸发；冰和雪均换算为液水当量。

{budget_table}

累计残差及冠层交换以 **SHAW 耦合域面积**加权；它们不是全流域水量平衡，也不能用来证明能量守恒。累计绝对残差先对每个 HRU 每天的残差取绝对值，再按面积加权和累计，避免不同地点或日期的正负误差互相抵消；最大单 HRU 日残差同时检查局地误差。汇总 JSON 另保留“先面平均、再逐日取绝对值”的统计，两个指标不能混用。程序保留 `0.1 mm/HRU/day` 的停止门槛，累计误差须结合模拟长度阅读。

{retry_table}

重试计数包括时间细分或附加交换系数导数的 HRU 小时，不是程序耗时。未收敛尝试先完整恢复状态，在同一步长下尝试包含冠层交换系数温度导数的迭代矩阵；仍不收敛再缩短步长，最多把一小时分成 64 段。两种矩阵求解相同的物理方程，采用相同的收敛门槛。未收敛结果不会自动接受或静默退回原始 SWAT+。

## 已核验的数值性质

{checks}

耦合桥接启用了冠层储量项迭代系数、叶片消元及根系非负供水修正，而官方参照试验采用保留原始算法的路径；两者不能混称为与官方算法逐位一致。根系修正通过重算有效供水土层避免吸水超过蒸腾，不以调整水量账本消除残差。降雪统计依据原始湿球温度规则记录截留前的大气降雪。状态隔离、冠层控制体交换及修正依据见 [数值审查记录](../NUMERICAL_AUDIT.md)。实现及试验入口：[SWAT 桥接](../../src/shaw_swat_module.f90)、[土柱接口](../../src/shaw/shaw_column_api.f90)、[列间状态试验](../../tests/test_shaw_columns.f90)、[动态冠层试验](../../tests/test_shaw_canopy.f90)、[根系试验](../../tests/test_shaw_roots.f90)、[交换系数导数试验](../../tests/test_shaw_conductance.f90)、[官方参照试验](../../tests/test_shaw_reference.f90)、[内核检查记录](kernel_checks.json)、[Ames 比较记录](ames_pristine.json)。

## 解释限制与后续验证

当前气孔和植被水力参数采用默认值；残茬层尚未由 SWAT+ 映射，管理引起的土壤物理参数变化尚未逐日同步。底部固定温度取气象发生器的年均气温，外部来水按接收土层温度进入，侧向系数缺乏独立各向异性资料。这些设置会影响水热分配，原 SWAT+ 参数也不能直接等价为 SHAW 参数。耦合 HRU 的 `esoil` 表示净蒸散扣除蒸腾后的剩余量，可能包含截留蒸发、雪升华或凝结，不能独立解释为裸土蒸发。

现有 SWAT+ 养分程序只处理向下渗漏。桥接保留 SHAW 内部有符号的水通量和水热状态，仅把土层底部日净水通量的正值传入这些旧程序，避免负渗漏造成养分凭空增加；未实现向上溶质输运，也未从这一总水通量中单独剔除水汽贡献。这是水热研究原型的兼容边界，不是完整溶质耦合。评价期耦合 HRU 的 {summary['transport_compatibility']['checks']['hru_daily_rows']:,} 条植被/气象记录中，25 个数值字段均为有限值，底部硝态氮输出均非负，见 [接口检查](transport_compatibility.json)。这项检查不能代替水质验证。

进一步判断科学增益，需要真实逐小时强迫、观测流量及积雪/土温资料，开展分模型率定和独立时段验证，并补充网格与时间步收敛、完整能量账本、深层边界敏感性和更多下垫面试验。水质代码保留并不意味着它对新水通量的适用性已通过验证。详细接口假设见 [耦合说明](../../SWAT_SHAW.md)。

## 复现标识

{table(['运行', '耗时（秒）', '完成时间（UTC）', '可执行文件 SHA256'], run_rows)}

耗时是本机此次运行记录，未控制重复次数与系统负载，不能作为稳定性能基准。原始输入和完整运行输出保留在本机，未随代码上传。

报告数据源哈希：

{hash_lines}

先完成四项运行及独立 HRU 检查，再依次执行 `tools/check_canada_column_parity.py`、`tools/analyze_canada.py` 和 `tools/write_canada_report.py`。报告生成器要求状态文件与汇总均完成、运行标识一致，并核对 9 条年度统计与 850 天日序列；任何运行重新开始后，必须重新生成分析，不能复用本报告。
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', type=Path, default=ROOT / 'reports/canada')
    args = parser.parse_args()
    directory = args.report_dir.resolve()
    summary = load_json(directory / 'summary.json')
    status = load_json(directory / 'analysis_status.json')
    if summary.get('status') != 'complete' or status.get('status') != 'complete' or status.get('errors'):
        raise ValueError('Report withheld: the three-model analysis has not completed successfully')
    with (directory / 'annual_comparison.csv').open(encoding='utf-8', newline='') as f:
        annual = list(csv.DictReader(f))
    with (directory / 'daily_comparison.csv').open(encoding='utf-8', newline='') as f:
        daily = list(csv.DictReader(f))
    validate(summary, status, annual, daily, ROOT / 'validation/canada')
    for name in ('process_comparison.png', 'process_comparison.pdf','seasonal_comparison.csv','hru_scope.csv',
                 'winter_spring_comparison.png','winter_spring_comparison.pdf','thermal_comparison.png','thermal_comparison.pdf'):
        if not (directory / name).is_file() or (directory / name).stat().st_size == 0:
            raise ValueError(f'Report withheld: missing comparison plot {name}')
    kernel_path = directory / 'kernel_checks.json'
    ames_path = directory / 'ames_pristine.json'
    kernel = load_json(kernel_path) if kernel_path.exists() else {}
    if kernel and kernel.get('coupled_executable_sha256') != summary['runs']['shaw']['sha256']:
        raise ValueError('Report withheld: kernel checks refer to a different coupled executable')
    ames = load_json(ames_path) if ames_path.exists() else {}
    if ames.get('coupling_off_run',{}).get('sha256') not in (None,summary['runs']['shaw']['sha256']):
        raise ValueError('Report withheld: Ames check refers to a different coupled executable')
    parity_path=directory/'basin_column_parity.json'
    parity=load_json(parity_path) if parity_path.exists() else None
    if parity and (parity.get('status')!='pass' or parity.get('coupled_executable_sha256')!=summary['runs']['shaw']['sha256']):
        raise ValueError('Report withheld: basin/isolated-column check is stale or unsuccessful')
    guard_path=directory/'minimum_step_guard_check.json'
    guard=load_json(guard_path) if guard_path.exists() else None
    if guard and (guard.get('status')!='pass' or guard.get('kernel_source_sha256')!=summary['runs']['shaw']['source_sha256']['src/shaw/shaw_water_heat.for']):
        raise ValueError('Report withheld: minimum-step check is stale or unsuccessful')
    names = ['summary.json', 'analysis_status.json', 'annual_comparison.csv', 'daily_comparison.csv','seasonal_comparison.csv','hru_scope.csv',
             'forcing_parity.json','transport_compatibility.json']
    names += [p.name for p in (kernel_path, ames_path) if p.exists()]
    if parity:names.append(parity_path.name)
    if guard:names.append(guard_path.name)
    hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names}
    report = render_report(summary, annual, daily, kernel, ames, hashes, parity, guard)
    output = directory / 'REPORT.md'
    output.write_text(report, encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

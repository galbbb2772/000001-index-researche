# RPC V2.0 — A股散户参与周期模型（冻结研究规格）

> 标的：上证综合指数 000001.SH  
> 状态：Research / Hypothesis Validation  
> 冻结日期：2026-11-15  
> 原则：先识别市场状态，不把状态分数直接当作买卖信号。

## 1. 核心假设

A股的大级别顶部与底部并不对称。

### 顶部机制
散户参与持续升温 → 全民狂热持续 → 新增参与边际衰竭 → 价格结构破坏。

### 底部机制
价格先发生严重损伤 → 散户参与进入冷漠区 → 风险承担资金停止去杠杆并重新回流 → Recovery Candidate。

因此顶部与底部必须使用不同状态机。

---

## 2. 数据制度桥接

### 2015 年以前
主变量：

```
AccountIntensity_t = 新增A股账户_t / 期初A股账户总量
```

### 2015 年以后
优先变量：

```
InvestorIntensity_t = 新增投资者_t / 期初投资者总数
```

原因：2015-04-13 放开“一人多户”后，“新增账户数”不再等价于“新增投资者人数”。

如果某阶段只能获得账户数：
- 允许作为相对热度、斜率、持续度代理；
- 禁止把绝对户数跨制度硬比较；
- 数据需标记 `PROXY_ACCOUNT_COUNT`。

### 统一桥接
跨制度不直接比较绝对值，而比较各制度内部的滚动相对强度/分位。

---

## 3. 顶部模块

### 3.1 RPI — Retail Participation Intensity
散户参与强度的制度内标准化版本。

### 3.2 RHI — Retail Heat Index
当前热度。设计原则：
- Level
- 3M slope
- acceleration
- 不把价格本身塞进 RHI，避免循环定义。

### 3.3 MPS — Mania Persistence Score
冻结核心定义：

```
MPS_t =
最近 6 个月中，
ParticipationIntensity >= 1.5 × 此前12个月中位数
的月份数量
```

MPS 只表达“狂热持续多久”，不表达价格顶部。

### 3.4 REI — Retail Exhaustion Index
描述参与绝对水平仍高、但斜率/加速度持续转弱的边际衰竭。

### 3.5 顶部状态机

```
EXPANSION
  ↓
MANIA
  ↓
EXHAUSTION
  ↓
TOP RISK
  ↓
TOP CONFIRMED
```

冻结的 Top Risk 机制：

```
MPS >= 3
AND 3M participation slope < 0
AND current monthly index return < 0
```

冻结的 Top Confirmed 价格破坏：

```
Top Risk
AND (
  current monthly return <= -10%
  OR compounded 2M return <= -12%
)
```

### 重要解释

- `MANIA`：参与极热，不等于顶部。
- `TOP_RISK`：脆弱性警报，不等于卖出信号。
- `TOP_CONFIRMED`：只有先存在持续狂热/衰竭，价格破坏才具有“泡沫死亡”含义。
- 单独的大跌不能制造顶部信号。

---

## 4. 底部模块

### 4.1 CSI — Capitulation Severity Index
连续环境变量，不设置单一魔法阈值。

候选构成：
- 过去6个月价格损伤；
- 距离过去12个月高点跌幅；
- 散户参与历史分位。

CSI 只描述“投降严重度”。

### 4.2 Apathy Zone
冻结候选定义：

```
ParticipationIntensity <= 过去24个月20%分位
AND
过去6个月指数收益 <= -10%
```

Apathy 是“区域”，不是时点。

### 4.3 Early Repair
价格出现技术修复，但融资/风险承担未恢复。

研究结论：
- 单月转正；
- 站上20MA；
- 突破20日/3个月高点；
- 单纯放量；

都容易被熊市反弹欺骗，因此不能单独定义 Recovery。

### 4.4 RCF-20 — Recovery Candidate Filter

冻结为最简单方向性条件：

```
Apathy Zone previously active
AND Close > MA20
AND MarginBalance_20D_Change > 0
```

解释：
- 不要求融资“大幅增长”；
- 只要求此前去杠杆状态停止，并首次转为正增长；
- 不再优化 0.5%、1%、2%、3% 等精确阈值。

RCF-20 的正式状态：

```
RECOVERY CANDIDATE
```

禁止称为：
- Bull Market Confirmed
- Major Bottom Confirmed
- Buy Signal

---

## 5. Bottom 状态机

```
CAPITULATION
  ↓
APATHY ZONE
  ↓
EARLY REPAIR
  ↓
RECOVERY CANDIDATE (RCF-20)
```

当前没有冻结“Recovery Confirmed”规则。

---

## 6. 已发现的失败案例/反例

### 2020
持续参与狂热存在，2020-09 形成 Top Risk；
但后续价格快速修复，未满足 Top Confirmed。

结论：
`Top Risk != Top Confirmed` 必须保留。

### 2011
进入长期冷漠区后仍可继续下跌。
价格站均线+放量仍会被熊市反弹欺骗。

结论：
`Apathy != Buy`；
`Price repair != Recovery`。

### 2022
RCF-20 OOS 只产生温和正收益，并不能证明“大底确认”。

结论：
RCF-20 只能保留为风险环境改善过滤器。

---

## 7. 已纠正的事后偏差

以下不能再作为“模型自动识别出的漂亮底部”：

- 2018-12
- 2022-10

它们是事后看起来更好的位置，不是冻结 Apathy 规则首次发信号的月份。

严格首次 Apathy 区域包括：
- 2018-06（随后仍可能继续下跌）
- 2022-04（随后仍有二次风险）

---

## 8. 2008 的处理

2008-10 是重要历史外部检查：
- 6M 价格损伤约 -53%；
- 相对过去12M高位跌幅约 -67%；
- A股开户强度相对 2007 狂热峰值下降约九成。

但因统一 24 个月参与分位 warm-up 不足：

```
2008 = PRE-SAMPLE EXTERNAL CHECK
```

禁止把它计入严格胜率/样本量。

---

## 9. Forward-OOS 冻结纪律

### Train / mechanism development
2012–2018

### OOS
2022

### Forward only
2024–2026

从本版本开始：

> 2024–2026 只能记录模型输出，禁止用于修改阈值。

---

## 10. 当前研究结论

### 顶部模块
有较清晰经济机制，但独立红灯样本极少；适合做稀有的大级别风险状态，不适合高频择时。

### Apathy
有长期信息含量，但不是交易时点。

### RCF-20
目前最值得保留的底部恢复过滤器，但证据仍弱，只能作为 `Recovery Candidate`。

### 总结
RPC 的目标不是“猜最高点/最低点”，而是改变对未来风险收益分布和市场状态的判断。

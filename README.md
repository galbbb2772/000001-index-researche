# 000001 Index Research

上证综合指数（000001.SH）研究仓库。

当前第一条正式研究主线：**RPC — Retail Participation Cycle / A股散户参与周期模型**。

## 研究目标

研究“新增投资者/新增A股账户的参与强度、持续度、衰竭，以及价格破坏/恢复”能否帮助识别：

- 全民散户泡沫的顶部风险；
- 极端下跌后的冷漠区；
- 冷漠区后的风险偏好恢复；
- 以及这些状态在 1/3/6/12 个月或 63/126/252 交易日后的收益与回撤分布。

## 当前版本

- **RPC V2.0 — frozen research specification**
- 顶部模块：RPI → RHI → MPS → REI → Price Damage
- 底部模块：CSI → Apathy Zone → RCF-20 → Recovery Candidate
- 2024–2026：**Forward/OOS only，不再用于调参**

## 重要研究纪律

1. 2015 年前后开户制度存在结构性断点，不能直接比较绝对开户户数。
2. 2015 年后优先使用中国结算“新增投资者数”；账户数只作为相对热度/斜率代理。
3. Top Risk ≠ Top Confirmed。
4. Apathy Zone ≠ 买入信号。
5. RCF-20 目前仅定义为 **Recovery Candidate**，不定义为“牛市确认”。
6. 小样本事件必须按独立周期去重，不能把连续月份当成多个成功样本。
7. 2022 已作为底部模块 OOS；2024–2026 不允许再参与阈值优化。

## 文件

- `research/RPC_V2_0_SPEC.md` — 模型逻辑、制度桥接、顶部/底部状态机
- `research/WALK_FORWARD_V1_0.md` — 训练/OOS 结果与失败案例
- `research/rpc_v2_0_frozen_spec.json` — 机器可读冻结规则

> 状态：research / hypothesis validation。当前不是独立交易策略，也不是实盘买卖指令。

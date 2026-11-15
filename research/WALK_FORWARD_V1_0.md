# Walk-Forward V1.0 — RPC Bottom / RCF-20

> 目的：停止边看历史边调参。  
> Train：2012–2018 独立冷漠周期  
> OOS：2022  
> Forward-only：2024–2026

## 1. 冻结训练事件

独立冷漠周期：
- 2012-08
- 2013-06
- 2018-06

冻结候选规则：

```
Apathy previously active
AND Close > MA20
AND MarginBalance change over ~20 trading days > threshold
```

训练阶段只比较宽阈值：
- >0%
- >0.5%
- >1%

## 2. 训练集结果

| Margin 20D | Avg Delay | 63D | 126D | 252D | 63D/126D/252D positive |
|---|---:|---:|---:|---:|---:|
| >0% | 49.3d | +8.2% | +5.5% | +7.4% | 3/3, 3/3, 3/3 |
| >0.5% | 49.3d | +8.2% | +5.5% | +7.4% | 3/3, 3/3, 3/3 |
| >1% | 50.7d | +10.9% | +5.8% | +7.5% | 3/3, 3/3, 3/3 |

训练集非常漂亮，因此必须做 OOS，不能直接宣布成功。

## 3. 2022 OOS

OOS 冷漠事件：
- Apathy trigger month：2022-04

### Threshold >0%

Signal：2022-05-30  
Delay：18 trading days  
Margin 20D change：+0.037%

Forward:
- 63D：+2.8%
- 126D：+0.5%
- 252D：+2.6%

Adverse excursion:
- 前63D：没有有效负向 excursion（原始最小路径仍高于触发价）
- 126D / 252D：约 -8.1%

### Threshold >0.5%

Signal：2022-05-31  
Forward:
- 63D：+1.7%
- 126D：-1.0%
- 252D：+1.3%

### Threshold >1%

Signal：2022-06-13  
Forward:
- 63D：-0.6%
- 126D：-2.4%
- 252D：-3.2%

## 4. OOS 结论

训练阶段“融资回升越强越可靠”的假设没有通过 2022 OOS。

真正可以保留的只是更弱、也更稳健的机制：

> 融资从下降转为正增长，比等待融资大幅增长更有意义。

因此不再优化精确幅度。

冻结：

```
MarginBalance_20D_Change > 0
```

而不是 0.5%、1%、2%、3% 等数据挖掘阈值。

## 5. 研究解释

RCF-20 的作用不是：
- 提高一年收益到很高；
- 精确抓住大底；
- 确认新牛市。

更合理的解释是：
- 避免在 Apathy 第一次出现时立刻抄底；
- 等待风险承担意愿第一次停止恶化；
- 把“极冷区域”升级成“恢复候选环境”。

正式评级：

```
RECOVERY CANDIDATE
evidence_strength = weak_to_moderate
independent_oos_events = 1
```

## 6. 预注册 Forward 纪律

2024–2026：
- 不允许参与阈值选择；
- 只记录当时可见信息；
- 不得用未来结果重写信号日期；
- 任何规则变化必须产生新版本并从变化日期后重新 Forward。

## 7. 失败/警示

- n 很小；
- 独立事件比月份数重要；
- 连续 Apathy 月份不能当成多个独立成功样本；
- 2018-12、2022-10 属于事后漂亮位置，不是首次冻结信号；
- 2008 因 warm-up 不足，只作为 pre-sample external check。

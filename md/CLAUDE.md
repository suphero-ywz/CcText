# 几何横版闯关 — 项目文档


## 项目概述

Python + Pygame 2D 横版动作闯关游戏。纯几何图形绘制（无美术素材），1 个手工精良关卡，近战攻击，参考 Hollow Knight 的紧凑手感。

- **语言/框架**: Python 3 + Pygame
- **视觉风格**: 彩色矩形/圆形代码绘制，无外部素材文件
- **窗口**: 800×600, 60 FPS, delta-time 物理
- **架构**: 8 个源文件，无子目录，单向依赖

---

## 文件结构

```
E:\study\cctext\
    main.py        — 入口、Game 类、状态机、主循环
    settings.py    — 所有常量（屏幕尺寸、颜色、物数值、敌人属性）
    player.py      — Player 类：移动、跳跃、近战攻击、血量、状态
    weapon.py      — 武器数据定义（剑/枪/斧）
    enemy.py       — BaseEnemy、PatrolEnemy、FlyingEnemy、BossEnemy
    level.py       — Level 类、关卡数据（ASCII 瓦片地图）、碰撞解析
    camera.py      — Camera 类：平滑跟随、震屏、视口限制
    ui.py          — HUD（血条/武器名）、菜单/暂停/死亡/胜利界面
    particles.py   — Particle + ParticleSystem（攻击命中、敌人死亡粒子）
```

**依赖关系**: `settings.py` + `weapon.py` ← 所有模块 ← `main.py`（无循环依赖）

---

## 游戏状态机

```
MENU → PLAYING → PAUSED → PLAYING
              → GAME_OVER → MENU
              → WIN → MENU
```

`Game.state` 字符串: `"MENU"` | `"PLAYING"` | `"PAUSED"` | `"GAME_OVER"` | `"WIN"`

---

## 核心系统设计

### 1. Player（player.py）

```
属性: rect, vx, vy, on_ground, facing(1/-1), hp, state, invincibility_timer,
      attack_cooldown_timer, attack_phase(startup/active/recovery/None)
```

- **移动**: 左右输入加速度 1600 px/s², 最大速度 280 px/s, 摩擦力 1000 px/s²
- **跳跃**: 可变高度（松键截断 vy *= 0.45，短按≈40% 满跳高度），起跳速度 -580 px/s
- **重力**: 1600 px/s², 终端下落速度 900 px/s
- **近战攻击**: 武器驱动的阶段机，三种武器（剑/枪/斧）各有独立参数和动画，详见武器系统
- **受伤**: 扣血 → 无敌 1.2s → 闪烁渲染
- **碰撞**: 轴分离（先 X 后 Y），与关卡瓦片碰撞解析
- **状态**: idle / run / jump / fall / attack / hit / dead

### 2. 武器系统（weapon.py）

三种武器，Q 键循环切换：

| 武器 | 伤害 | 冷却 | 穿透 | 判定框 | 动画 |
|------|------|------|------|--------|------|
| 剑 (Blade) | 1 | 0.35s | 否 | 36×40 | 弧形横扫 |
| 枪 (Spear) | 1 | 0.50s | 是 | 56×28 | 直线突刺 |
| 斧 (Greatsword) | 2 | 0.65s | 否 | 40×48 | 竖劈砸地 |

- 武器定义为 dict，存储在 `WEAPONS` 列表
- `player._weapon` property 读取当前武器参数
- 攻击逻辑（阶段机、判定框、动画）均从 weapon dict 读取，无硬编码

### 3. 关卡（level.py）

- **数据格式**: Python 字典常量 `LEVEL_1_DATA`，含 ASCII 瓦片地图
- **瓦片**: `G`=地面(碰撞, DARK_GRAY), `P`=平台(碰撞, MID_GRAY), `B`=背景(无碰撞, 暗色), ` `=空气
- **规模**: 20 行 × 160 列, 每瓦片 32×32 px → 5120×640 像素
- **碰撞优化**: 只查询实体周围扩界矩形内的瓦片
- **碰撞算法**: X 轴移动 → 推离 → Y 轴移动 → 推离 → 检测 on_ground

### 4. 敌人（enemy.py）

- **BaseEnemy**: 公共属性(rect, vx, vy, hp, color, damage, alive)，受伤/死亡/渲染
  - 受伤时白色闪烁 + 击退，死亡时生成粒子
  - 敌人受伤闪烁 + 击退
- **PatrolEnemy**: 地面巡逻 70 px/s，撞墙/崖边掉头，可选 patrol_range 限制
- **FlyingEnemy**: 无视重力，正弦悬停 ±15px，玩家进入 250px 范围后追踪
- **BossEnemy**: 80×80, HP=20, 伤害=2
  - 巡逻 → 蓄力 → 冲撞(320 px/s) → 眩晕 0.8s 循环
  - 半血进 P2：颜色变红橙，速度加快，增加跳跃砸地招式
  - Boss 受伤击退减半(×0.3)

### 5. Camera（camera.py）

- **平滑跟随**: `offset += (target - offset) * min(5.5 * dt, 1.0)`
- **前瞻**: target 加入 `player.vx * 0.3`，跑动时看到更多前方
- **限幅**: 不超关卡像素边界
- **Boss 战锁场**: 进入 Boss 区域(关卡数据中 boss_arena_start 列)后右边界锁死
- **震屏**: `shake(intensity, duration)`, Boss 攻击(intensity=10)、玩家受伤(4)、Boss 死亡(20)

### 6. 粒子系统（particles.py）

- Particle: x, y, vx, vy, lifetime, color, size; 受重力影响，衰减后淡出
- ParticleSystem: `emit()`, `enemy_death()`, `attack_hit()`
- 攻击命中: 5-8 个白/黄色粒子沿攻击方向飞溅
- 敌人死亡: 15-20 个该敌人颜色的粒子爆炸

### 7. UI（ui.py）

- **血条**: 背景条+前景条(绿→黄→红渐变)，白边框
- **HUD**: 左上玩家血条，顶部居中 Boss 血条(含标签"BOSS")
- **菜单**: 标题"GEOMETRIC BLADE"，"Press ENTER to start"
- **暂停**: 半透明暗色遮罩 + "PAUSED"
- **游戏结束**: "GAME OVER" + "Press ENTER to retry"
- **胜利**: "VICTORY" + "Press ENTER to return to menu"
- **字体**: `pygame.font.Font(None, size)` 默认字体，三档尺寸(20/36/64)

### 8. 手感系统

- **顿帧(Hitstop)**: 攻击命中时冻结 update 0.05s（渲染继续），Boss 命中 0.08s
- **攻击判定可视化**: Active 帧画亮色判定框

---

## 颜色方案

| 颜色 | RGB | 用途 |
|------|-----|------|
| BLACK | (10,10,15) | 通用暗色 |
| WHITE | (240,240,240) | 文字/高亮 |
| BLUE | (50,80,220) | 玩家 |
| RED | (220,50,50) | Boss P1 / 受伤 |
| ORANGE | (240,140,40) | 巡逻敌人 |
| PURPLE | (180,60,220) | 飞行敌人 |
| GREEN | (50,220,50) | 血条满血 |
| YELLOW | (240,220,40) | 攻击特效 |
| DARK_GRAY | (40,40,50) | 地面瓦片 |
| MID_GRAY | (90,90,105) | 平台瓦片 |
| BG_COLOR | (20,20,30) | 背景 |

---

## 控制

| 按键 | 功能 |
|------|------|
| A / ← | 左移 |
| D / → | 右移 |
| W / ↑ / Space | 跳跃 |
| J / Z | 攻击 |
| Q | 切换武器 |
| ESC / P | 暂停 |
| ENTER | 菜单确认 |

---

## 关键物数值（调优起点）

| 参数 | 值 | 说明 |
|------|-----|------|
| PLAYER_SPEED_ACCEL | 1600 px/s² | 水平加速度 |
| PLAYER_MAX_SPEED | 280 px/s | 最大水平速度 |
| PLAYER_FRICTION | 1000 px/s² | 松键减速度 |
| PLAYER_GRAVITY | 1600 px/s² | 重力 |
| PLAYER_JUMP_VEL | -580 px/s | 起跳速度 |
| PLAYER_MAX_FALL | 900 px/s | 下落终端速度 |
| PLAYER_JUMP_CUT | 0.45 | 松键跳跃截断系数 |
| PLAYER_MAX_HP | 5 | 玩家血量 |
| CAMERA_LERP_SPEED | 7.0 | 摄像机跟随速度 |

---

## 渲染顺序

1. 背景填充 BG_COLOR
2. 关卡瓦片（先背景装饰 B，再实体 G/P）
3. 粒子
4. 敌人（按 Y 排序）
5. Boss
6. 玩家
7. HUD / UI 覆盖层（不受摄像机偏移影响）

---

---

## 项目进度

### 阶段 1：核心引擎 [x] 已完成
**目标**: 玩家能在地图上跑跳，摄像机跟随

- [x] `settings.py` — 所有常量定义
- [x] `main.py` — Game 类骨架、状态机、主循环（先只渲染空白背景）
- [x] `level.py` — Level 类、测试用小地图、瓦片渲染、碰撞解析
- [x] `camera.py` — Camera 类、平滑跟随、视口限幅
- [x] `player.py` — Player 类（仅移动+跳跃，无攻击）
- [x] P1 集成 — main.py 串联：玩家在地图上跑跳，摄像机跟随

**可验证**: 运行 `python main.py`，看到一个蓝色矩形在灰色平台上跑跳

### 阶段 2：战斗 [x] 已完成
**目标**: 能攻击敌人，有粒子反馈，有受伤和血量

- [x] `player.py` — 近战攻击阶段机、判定框、冷却
- [x] `enemy.py` — BaseEnemy、PatrolEnemy（巡逻 AI、受伤、死亡）
- [x] `particles.py` — Particle、ParticleSystem、攻击命中/死亡粒子
- [x] P2 集成 — 攻击判定、敌人接触伤害、玩家血量、无敌帧

**可验证**: 能用 J 键攻击敌人，击败后粒子爆炸效果，碰敌人会受伤

### 阶段 3：关卡制作 [x] 已完成
**目标**: 完整可玩的精美关卡

- [x] `level.py` — 设计 LEVEL_1_DATA（160×20 ASCII 地图）
- [x] `enemy.py` — FlyingEnemy（悬停+追踪）
- [x] P3 集成 — 关卡敌人布设、`spawn_enemies()` / `spawn_boss()`

**可验证**: 整关可从头走到 Boss 区域入口，沿途有敌人

### 阶段 4：Boss 战 [x] 已完成
**目标**: Boss 战完整、可通关

- [x] `enemy.py` — BossEnemy（巡逻→蓄力→冲撞→眩晕，P1/P2 双阶段）
- [x] `camera.py` — Boss 区域镜头锁定
- [x] `main.py` — Boss 血条显示、胜利条件
- [x] `camera.py` — 震屏功能

**可验证**: 击败 Boss 触发胜利状态

### 阶段 5：UI & 打磨 [x] 已完成
**目标**: 完整游戏体验，菜单/暂停/死亡/胜利全串联

- [x] `ui.py` — 全部 UI 界面（菜单、暂停、死亡、胜利、HUD）
- [x] `main.py` — 完整状态机串联、reset_game()
- [x] 顿帧系统（hitstop_timer）
- [x] 数值调优（物数值手感调整）
- [x] 最终测试：整关可从菜单→通关→回菜单完整走通

**可验证**: 完整游戏循环：菜单→游戏→死亡→重试 / 通关→胜利→菜单

### 阶段 6：武器系统 [x] 已完成
**目标**: 多武器切换，差异化战斗手感

- [x] `weapon.py` — 三种武器 dict 定义（剑/枪/斧）
- [x] `player.py` — 攻击逻辑武器驱动，三种动画（弧扫/突刺/竖劈）
- [x] `main.py` — Q 键切换，枪穿透多目标，斧额外震屏
- [x] `ui.py` — 武器名 HUD，菜单 Q 键提示

**可验证**: Q 键在三种武器间切换，各有不同的攻速/射程/伤害/动画

---

## 待定 / 后续可扩展


- [x] 武器系统（剑/枪/斧，Q 键切换）
- [ ] 音效系统（Pygame mixer）
- [ ] 更多关卡（只需新增 LEVEL_2_DATA 等数据）
- [ ] 更多敌人类型
- [ ] 玩家技能升级 / 道具系统
- [ ] 关卡编辑器
- [ ] 键位自定义
- [ ] 手柄支持
- [ ] 尖刺即死陷阱（`S` 瓦片已预留）

---


## 开发注意事项

- 所有物数值集中在 `settings.py`，调优只改这一个文件
- 碰撞解析统一走 `level.resolve_collisions()`，Player 和 Enemy 共用
- 摄像机 `apply()` 方法转换世界坐标→屏幕坐标，渲染时都经它过一遍
- 粒子系统在每个 enemy 的 `die()` 和 player 攻击命中时触发
- `reset_game()` 用于重新开始，不重启进程
- 调试时可加 F1 键显示瓦片网格和碰撞框（可选实现）

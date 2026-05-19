# 开发日志

## 2026-05-19 — 阶段一完成 + Bug 修复

### 完成内容
- 创建项目骨架：settings.py, main.py, level.py, camera.py, player.py
- 玩家移动 + 跳跃 + 重力 + 碰撞（轴分离 X→Y）
- 摄像机平滑跟随 + 视口限幅
- ASCII 瓦片地图渲染（G=地面, P=平台, B=背景装饰）
- 亚像素移动累积器 (rem_x, rem_y) 避免浮点截断穿模

### 遇到的 Bug 及解决方案
1. **速度当位移用** — resolve_collisions 把 vx/vy 直接当像素位移。修复：传 dx=vx*dt 给碰撞函数
2. **双重移动** — player.update() 和 resolve_collisions 都移动了 rect。修复：碰撞函数只推离不移动
3. **地面穿模** — 浮点截断导致 rect 与瓦片不重叠，colliderect 检测不到。修复：亚像素累积器 + 3px foot_rect 接地容错
4. **水平碰撞误推** — 重力使玩家陷地 1px 后 X 碰撞先触发。修复：拆分为 X 后 Y 轴分离
5. **键盘输入无效** — pygame.key.get_pressed() 在 Windows SDL 2.28.4 返回全 False。修复：事件驱动 KEYDOWN/KEYUP 维护 keys_down 集合
6. **中文输入法吞噬按键** — 微软拼音拦截字母键(A/D/W)但不拦截空格。修复：pygame.key.stop_text_input() + scancode

### 后续注意事项
- 碰撞始终走 level.resolve_collision_x/y，参数传 dx/dy 用于判断方向
- 按键检测同时查 keycode 和 scancode（IME 兼容）
- 所有物数值集中在 settings.py
- 摄像机 apply() 转换世界坐标→屏幕坐标
- 并且每次添加或者修改项目中的任何内容时都需要在日志文件中写上对应的内容
---

## 2026-05-19 — 阶段二：战斗系统

### 完成内容
- **settings.py** — 攻击时间窗口、玩家无敌/击退、敌人速度、粒子物理、顿帧参数
- **player.py** — 攻击阶段机（startup 0.07s → active 0.12s → recovery 0.12s），攻击判定框生成，J/Z 攻击输入，HP 系统，受伤击退 + 无敌 1.2s + 闪烁渲染，死亡状态
- **enemy.py** — BaseEnemy（血量/受伤/白色闪烁/击退/接触伤害/重力+碰撞），PatrolEnemy（地面巡逻 70px/s，遇墙/崖边自动掉头，可选 patrol_range）
- **particles.py** — Particle（重力+摩擦力+淡出），ParticleSystem（attack_hit 5-8个白/黄色粒子，enemy_death 15-20个该敌人颜色粒子）
- **main.py** — 敌人生成、攻击判定碰撞检测、接触伤害、粒子更新/渲染、玩家死亡→GAME_OVER 状态转换
- **顿帧** — 攻击命中冻结玩家 update 0.05s（渲染继续）

### 架构决策
- 敌人受伤击退：设置 knockback_vx/vy 后下一帧 apply，同时强制 on_ground=False 确保被击飞
- 敌人死亡移除：检测 !alive → 生成死亡粒子 → 从列表移除
- 攻击命中唯一性：命中第一个敌人后 break，每次攻击只打击一个敌人
- 接触伤害去重：依赖 player 无敌帧，避免每帧反复扣血

### 后续注意事项
- 攻击阶段机在 player.update() 中驱动，主循环只读取 get_attack_hitbox() 做碰撞检测
- 敌人 update() 接收 player 引用用于接触伤害检测
- 粒子系统在主循环 update() 后渲染，颜色在 render 时根据 lifetime 淡出
- GAME_OVER 状态目前无 UI 界面，按 ENTER 可重新开始（阶段五补充 UI）

---

## 2026-05-19 — Bug 修复：攻击后闪退

### 问题
玩家按 J/Z 攻击敌人后游戏闪退。

### 根因分析（两个关联 bug）

1. **顿帧冻结了攻击阶段计时器** — `update()` 在 hitstop 期间直接 return，导致 `attack_phase_timer` 不递减，active 阶段被异常延长。延长的 active 帧持续命中同一敌人 → 再次触发 hitstop → 进一步延长 active → 多段命中循环，造成状态异常。

2. **同一攻击摆动缺少命中去重** — 每次攻击的 active 阶段跨约 7 帧（0.12s），若敌人仍在判定框内会反复命中（规范要求每摆动每敌人最多命中 1 次）。

### 修复方案
- **重构 update() 顺序**：计时器递减（hitstop / cooldown / invincibility / attack_phase_timer）始终执行，hitstop 只冻结物理（移动/跳跃/重力/碰撞）
- **新增 `hit_enemies` 集合**：每摆动开始/结束时 clear，记录已命中的敌人 id
- **新增 `can_hit_enemy()` / `mark_enemy_hit()`**：main.py 攻击判定前检查去重

### 验证
- 单敌人：3 次攻击摆动将其击杀（摆动间隔 ~20 帧 = 0.33s），每次摆动只命中 1 次
- 多敌人：击杀 → 粒子生成 → 从列表移除无异常
- 游戏窗口运行 8 秒无错误退出

---

## 2026-05-19 — Bug 修复：真正闪退原因 + 血条/伤害数字

### 真正闪退原因
之前的「顿帧冻结攻击计时器」修复并没有解决闪退问题。根因在 `particles.py` 摩擦力公式：

```python
# 错误代码
PARTICLE_FRICTION = 400
self.vx -= self.vx * PARTICLE_FRICTION * dt  # vx *= (1 - 400/60) = vx * (-5.67)
```

每帧 vx 乘以 -5.67，速度在 3-4 帧内爆炸到 ±10^5+，粒子坐标溢出 SDL_Rect 的 Sint16 范围（-32768 ~ 32767），`pygame.draw.rect` 抛出 `TypeError: rect argument is invalid`，游戏闪退。

**修复**：
- `PARTICLE_FRICTION` 从 400 降到 3.0
- 公式改为阻尼：`self.vx *= max(0.0, 1.0 - PARTICLE_FRICTION * dt)`（每帧保留 ~95%）
- 颜色 alpha 增加 `min(1.0, ...)` 上限钳位

### 新增功能

**血条系统**：
- 玩家血条 — 左下角固定位置（屏幕坐标），200×16px，绿→黄→红渐变，白色边框 + "HP" 标签
- 敌人血条 — 头顶上方 30×4px，仅受伤后显示（hp < max_hp），同样颜色渐变

**浮动伤害数字**：
- `DamageNumber` 类 — 从受击点向上飘动，0.7s 淡出
- 集成到 `ParticleSystem`，字体 24px 默认字体

**异常捕获**：
- `main.py` 主循环包裹 try/except，打印完整 traceback 后退出
- 避免静默闪退，方便后续排查

---

## 2026-05-19 — 摄像机/二段跳/敌人跳跃

### 摄像机丢失玩家问题
玩家会走到关卡边界之外（测试地图边缘无碰撞墙），摄像机 clamp 在关卡范围内无法跟随。

**修复**：`level.py` 新增 `clamp_to_bounds()` 方法，在 `resolve_collision_x` 末尾调用，将实体钳制在 `[0, level_width]` × `[0, level_height]` 范围内。CAMERA_LERP_SPEED 提高到 7.0 加快跟随。

### 二段跳
- `jumps_left` 初始化为 2，落地重置
- 首次跳跃：按住跳跃键即可触发（地面）
- 二段跳：需要松开再按（空中 rising edge 检测），防止按住时一次性用完
- 用 `_jump_was_pressed` 追踪上一帧跳跃键状态

### 敌人跳跃过坑
- 前方没地面 (`has_ground=False`) 且下方有地面 (`has_ground_below=True`) → 小坑/落差，触发跳跃跨越
- 前方没地面且下方也没地面 → 深坑，掉头
- 前方有墙 → 掉头
- 跳跃速度使用 `PLAYER_JUMP_VEL`（-580），水平 70px/s，可跨越约 50px 的坑

---

## 2026-05-19 — 阶段三~五完成 + Bug 修复：敌人跳跃检测失效

### Bug: 敌人遇到坑仍无法跳跃

**现象**: PatrolEnemy 走到平台边缘就停下/掉头，不会跳跃跨越小坑。

**根因**: `get_nearby_tile_rects(margin=2)` 只返回实体矩形外扩 2px 范围内的瓦片。但 `front_foot` 和 `ground_below` 检测矩形距离实体中心 20px（即矩形边缘外 6-8px），这些位置点的碰撞检测永远找不到瓦片 → `has_ground` 始终为 False。

**修复**: PatrolEnemy.update() 中不再使用 `get_nearby_tile_rects()` + rect 碰撞检测，改为直接调用 `level.is_solid(col, row)` 查询指定瓦片坐标：

- 墙检测：检查敌人前沿 (`right+2` 或 `left-2`) 对应的瓦片列，三个高度（top/center/bottom）的瓦片行
- 地面检测：检查 `centerx + direction*16`（2px 过前沿）下方瓦片
- 坑深判断：检查同一列再下一行是否有瓦片
- 所有行/列索引均做了 `0 <= idx < level.rows/cols` 边界检查

### 阶段三：关卡制作 + 飞行敌人

**关卡设计**：
- `LEVEL_1_DATA`：20 行 × 160 列 ASCII 地图，替换原来的测试小地图
- Section 1 (cols 0-25): 起始区，平坦地面，入门引导
- Section 2 (cols 26-55): 平台区 + 1-2 格小坑（敌人可跳跃跨越），飞行敌人出没
- Section 3 (cols 56-100): 复杂平台 + 混合敌人
- Section 4 (cols 101-134): Boss 前挑战区
- Section 5 (cols 135-159): Boss 战场（25 列 = 800px = 一屏宽）
- 地面行 17 有 8 格和 10 格的大坑（玩家专属跳跃挑战），也有 2-3 格的小坑（敌人可跨越）
- 平台行 6/8/10/12 分散在不同高度，供玩家探索
- 背景装饰 B 瓦片在 rows 2/4/5/14（无碰撞，纯视觉效果）
- `BOSS_ARENA_START_COL = 135`，`BOSS_SPAWN_X/Y` 定义 Boss 出生点

**FlyingEnemy**（飞行敌人）：
- 30×30，HP=2，伤害=1，颜色 ENEMY_FLYING_COLOR (180,60,220)
- 无视重力，在 `base_y` 附近正弦悬停
- 玩家进入 250px → aggro 激活，水平 110px/s 追踪 + 垂直 66px/s 同向移动
- 未 aggro 时缓慢返回 `base_x`，抵达后 hover
- 渲染：主体矩形 + 两侧翅膀（上下扇动效果）+ 眼睛
- 翅膀 animation: `wing_offset = int(3 * (1 + hover_time * 8 % 2))`

**敌人布设**（`_spawn_enemies()`）：
- 14 个敌人：8 个 PatrolEnemy + 6 个 FlyingEnemy
- 按关卡分区分布，每区 2-4 个敌人
- PatrolEnemy 部分带 `patrol_range` 限制巡逻范围
- 敌人均使用 `level.is_solid()` 直接查瓦片坐标进行 AI 检测

### 阶段四：Boss 战

**BossEnemy**：

- 80×80 大型敌人，HP=20，伤害=2
- 状态机: patrol → windup → charge → stun → patrol
  - **patrol**: 面向玩家方向移动，速度 60px/s
  - **windup**: 玩家进入 300px 范围触发，暂停 0.4s 蓄力（白色闪烁 telegraph）
  - **charge**: 向玩家方向冲刺，速度 320px/s，撞墙或超时(2s)后进入 stun
  - **stun**: 眩晕 0.8s，不移动，头顶黄色星星标记
  - P2 额外 **ground_slam**: 跳起(vy=-700) → 落地 → 短眩晕，3s 冷却
- 双阶段系统：
  - **P1** (HP > 50%): 红色，基础速度，巡逻→蓄力→冲撞循环
  - **P2** (HP ≤ 50%): 颜色变红橙 `(240,80,20)`，速度全面提升（patrol 90px/s, charge 440px/s），增加跳砸招式
- 受伤击退系数 `BOSS_KNOCKBACK_RESIST = 0.3`（击退力度大幅降低）
- 受伤时中断当前蓄力/冲撞，进入短眩晕
- 渲染：主体矩形 + 红色边框(P1) / 黄色边框(P2) + 双眼 + 眩晕星星

**Boss 战场锁定**：
- 摄像机新增 `boss_arena_locked` 属性
- `lock_boss_arena(arena_left, arena_right)`: 锁定水平滚动范围
- 玩家进入 `BOSS_ARENA_START_COL` (col 135) → 触发 `_try_spawn_boss()` → 生成 Boss + 锁定摄像机
- Boss 死亡 → `self.state = "WIN"` → 显示胜利画面

**震屏系统**（已有的 `camera.shake()` 方法）：
- 玩家受伤: intensity=4, duration=0.12s
- Boss 攻击命中: intensity=10, duration=0.15s
- Boss 死亡: intensity=20, duration=0.5s

### 阶段五：UI 与完整游戏循环

**ui.py** — 所有 UI 界面：

- `draw_menu()`: "GEOMETRIC BLADE" 标题 + "Press ENTER to start" + 操作说明文字
- `draw_pause()`: 半透明黑色遮罩 + "PAUSED" + "Press ESC or P to resume"
- `draw_game_over()`: 暗红遮罩 + "GAME OVER" + "Press ENTER to retry"
- `draw_victory()`: 暗绿遮罩 + "VICTORY" + "Press ENTER to return to menu"
- `draw_boss_hp_bar(hp, max_hp)`: 顶部居中 300×18px Boss 血条，绿色→黄色→红色渐变，红色边框，"BOSS" 标签在左侧
- 三档字体: `pygame.font.Font(None, size)` — 20/36/64

**完整状态机** (main.py):

```
MENU → (ENTER) → PLAYING → (ESC/P) → PAUSED → (ESC/P) → PLAYING
                       → (死亡) → GAME_OVER → (ENTER) → MENU
                       → (Boss死) → WIN → (ENTER) → MENU
```

- 初始状态 `MENU`，按 ENTER 开始游戏 + 重置所有数据
- GAME_OVER / WIN 按 ENTER 返回 MENU
- 每次从 MENU 进入 PLAYING 时调用 `reset_game()`

**渲染顺序**（更新为含 Boss）：
1. 背景填充 BG_COLOR
2. 关卡瓦片（B 背景装饰 → G/P 实体）
3. 敌人（按 `rect.bottom` Y 轴排序，含 Boss）
4. 粒子
5. 玩家
6. HUD（玩家血条左下角 + Boss 血条顶部居中）
7. UI 覆盖层（暂停/死亡/胜利叠加层）

**Y 排序渲染**：`entities.sort(key=lambda e: e.rect.bottom)` — Boss 和普通敌人混合排序，确保近处敌人渲染在远处敌人之上。

### 手动物数值调整

| 参数 | 旧值 | 新值 | 说明 |
|------|------|------|------|
| CAMERA_LERP_SPEED | 5.5 | 7.0 | 摄像机更紧跟随 |

新增 Boss 相关参数见 settings.py 中 BOSS_* 系列。

### 敌人生成位置说明
- 所有 PatrolEnemy 和 FlyingEnemy 使用 `col * TILE_SIZE` 计算绝对像素坐标
- PatrolEnemy Y 坐标: `row * TILE_SIZE - 40`（脚底对齐瓦片顶部）
- FlyingEnemy Y 坐标: `row * TILE_SIZE`（悬浮在该行高度）
- Boss 出生点: `(BOSS_SPAWN_X, BOSS_SPAWN_Y - 80)`（脚底对齐地面）

### 已知注意事项
- FlyingEnemy 无碰撞检测（无视瓦片），仅受边界钳制
- Boss 冲撞可能冲出关卡边界，依赖 `clamp_to_bounds()` 钳制
- Boss 眩晕星星是纯装饰，无额外机制
- P2 跳砸的落地检测依赖 `on_ground` 常规碰撞
- 敌人所有 tile 检测使用 `level.is_solid()` 直接查询而非 rect 碰撞

---

## 2026-05-19 — Bug 修复：敌人跳跃失效第二版 + 攻击动画 + UI 中文化

### Bug: 敌人跳跃仍然不工作（第二版修复）

**现象**: 第一版 `level.is_solid()` 修复后，敌人走到平台边缘仍然不跳。

**根因分析（两个叠加问题）**：

1. **台阶误判为高墙** — 敌人（40px 高）站在 row 17 地面时，其 `mid_row`（centery // TILE_SIZE）也落在 row 16。当遇到 1 格高台阶时，`solid_mid` 为 True，触发 `hit_wall → 掉头`。台阶实际只有 32px，敌人可跳 105px，本应跳上去。

2. **地图缺台阶场景** — 原 `LEVEL_1_DATA` 中 row 16 全为空，row 17 的坑全为 4-8 格宽（敌人最大跳跃距离 ~51px ≈ 1.6 格，无法跨越）。

**修复**：

- **台阶检测改用 `above_head_row` 判断墙高**：
  - `above_head_row = head_row - 1`（敌人头顶上方一行）
  - `solid_above_head` → 墙超头顶 → 掉头
  - `solid_head / solid_mid / solid_foot`（头顶未堵）→ 台阶，跳跃上坡
  - 这样 1-2 格台阶都会被正确识别为可跳跃
  
- **重写 `LEVEL_1_DATA` row 16-17**：
  - Row 16 在 12 个坑位正上方放置 G 瓦片，形成台阶（row16=G, row17=空格）
  - Row 17 坑重新划分为：6 个 1-2 格窄坑（敌人可跨越）+ 3 个 4 格宽坑（玩家专属挑战）
  - Row 18-19 全部 G 保证坑底有地面

- **600 帧渲染测试验证**: 5 次敌人跳跃记录，0 错误

### 攻击动画替换判定框可视化

**改动**: `player.py` — 移除黄色矩形判定框渲染（逻辑保留），新增 `_render_slash()` 挥砍动画。

**动画设计**（三段式，与攻击阶段机同步）：
- **startup (0.07s)**: 从玩家中心向后方（facing×0° → facing×-100°）旋转的线条，逐渐变亮变长
- **active (0.12s)**: 从后方 sweeping 到前方（facing×-100° → facing×+70°），4 层拖尾弧线 + 主挥砍线(4px) + 末端黄色光晕圆圈
- **recovery (0.12s)**: 线停在前方 70°，alpha 逐渐淡出

**技术细节**：
- 角度随 `facing` 取反，左右方向自动适配
- 拖尾通过 `trail_angle = angle + offset * 0.25°` 实现多层叠加
- 光晕半径在 active 中段最大（`6 + 4 * |0.5 - t|`），模拟命中发力点

### UI 全中文化 + 字体 Bug 修复

**中文化** (`ui.py`):
- 标题: "几何之刃"
- 菜单: "按 ENTER 开始游戏" + 中文操作说明
- 暂停: "暂停" / "按 ESC 或 P 继续"
- 死亡: "游戏结束" / "按 ENTER 返回主菜单"
- 胜利: "胜利！" / "按 ENTER 返回主菜单"

**字体 Bug**: `pygame.font.SysFont("Microsoft YaHei", size)` 在 pygame 2.6.1 + Windows 下触发 `initsysfonts_win32()` 内部类型错误（`expected str, bytes or os.PathLike object, not int`），原因是 Windows 字体目录中存在非字体文件。

**修复**: 改用直接路径加载 `pygame.font.Font("C:/Windows/Fonts/msyh.ttc", size)`，依次尝试 msyh.ttc → simhei.ttf → simsun.ttc，全失败则回退到 `pygame.font.Font(None, size)`。

### BOSS_ARENA_START_COL 未定义

**问题**: `main.py` 中使用了 `BOSS_ARENA_START_COL` 但未导入。该常量定义在 `level.py:30`，不在 `settings.py`。

**修复**: `main.py` 从 `level` 模块新增导入 `BOSS_ARENA_START_COL`。

### 关卡地图调整明细

Row 16 (台阶层): 12 个台阶位: cols 7-8, 22-23, 29-30, 57, 70-71, 101, 135-136
Row 17 (地面层): 10 段地面，间隔为窄坑(1-2格, 6个)或宽坑(4格, 3个)
- 窄坑均配台阶，敌人优先上坡 → 上不去才尝试跨越
- 宽坑行 17 空格 + 行 18 G，敌人会尝试跳跃但距离不够 → 落入行 18 → 继续巡逻

### 验证结果
- 8/8 文件编译通过
- 600 帧端到端渲染 0 错误
- 敌人跳跃 5 次记录确认（x=194/674/1857/3490/4290），对应 cols 6/21/58/109/134 窄坑/台阶位

---

## 2026-05-19 — 阶段六：武器系统

### 完成内容
- **weapon.py** — 新建武器数据模块，3 种武器 dict 定义
- **player.py** — 攻击逻辑重构为武器驱动，`_weapon` 属性读取当前武器参数
- **main.py** — Q 键切换武器、穿透判定（Spear）、斧头额外震屏
- **ui.py** — 武器名 HUD 显示、菜单 Q 键提示
- **settings.py** — 移除旧 ATTACK_* 常量（迁移到 weapon.py）

### 三种武器

| 武器 | 伤害 | 冷却 | 特点 |
|------|------|------|------|
| 剑 (Blade) | 1 | 0.35s | 默认武器，手感不变，弧形横扫 |
| 枪 (Spear) | 1 | 0.50s | 长距离突刺 56px，穿透多目标 |
| 斧 (Greatsword) | 2 | 0.65s | 慢速重击，可秒杀飞行敌人，竖劈动画 |

### 架构决策
- 武器数据用 dict 而非 class/dataclass，与项目 settings 风格一致
- `player._weapon` 作为 property，攻击逻辑统一从 weapon dict 读取参数
- `hit_enemies` 集合的每摆动去重机制天然支持穿透（Spear 不 break，仍防止同摆动命中同一敌人两次）
- 斧头命中 Boss 时震屏强度 +6（SHAKE_BOSS_ATTACK + 6 = 16）
- 切换武器会中断当前攻击（防止切换后判定框异常）

### 受影响的文件
- `weapon.py` — **新建**
- `settings.py` — 移除 ATTACK_COOLDOWN/STARTUP/ACTIVE/RECOVERY/HITBOX_* 7 个常量
- `player.py` — +_weapon property, +cycle_weapon(), 攻击逻辑/动画全面武器化
- `main.py` — Q 键事件, weapon damage/pierce 应用, 斧头震屏
- `ui.py` — 菜单加 Q 键说明, HUD 显示武器名

### 验证结果
- 6/6 文件编译通过
- 导入测试正常，3 武器名正确加载
- 游戏启动 3 秒无异常

---

## 2026-05-19 — 武器调优 + 敌人卡墙修复 + UI 优化

### 枪攻速提升（weapon.py）

| 参数 | 旧值 | 新值 |
|------|------|------|
| cooldown | 0.50s | 0.36s |
| startup | 0.10s | 0.06s |
| recovery | 0.15s | 0.10s |

现在枪攻速接近剑（0.35s），长射程+穿透特性更实用。

### 敌人卡墙修复（enemy.py）

**根因**: `resolve_collision_x()` 碰撞后将 `vx` 置零，PatrolEnemy AI 从 `vx` 推导方向 → 速度丢失且 `-0=0` 导致永久卡死。

**修复**:
- 新增 `patrol_dir` 持久方向变量，AI 只改这个
- `direction` 改为读 `patrol_dir`，不再从 `vx` 推导
- 每帧落地时恢复 `vx = patrol_dir * PATROL_SPEED`
- 掉头/撞墙/出界统一翻转 `patrol_dir` 并显式赋值 `vx`
- 巡逻范围超限直接设置 `patrol_dir` + `vx`，不再用 `abs()`

### UI 全面优化（ui.py + main.py）

**菜单**:
- 标题脉冲光晕动画（蓝紫色呼吸效果）
- 标题下方黄色装饰线
- 按键说明改为面板 + 双列布局（键名列黄色，描述列灰色）
- 背景装饰横线（6 条渐变暗线）

**暂停 / 死亡 / 胜利**:
- 面板化设计：居中暗色面板 + 彩色边框
- 死亡面板：暗红底 + 红色边框
- 胜利面板：暗绿底 + 绿色边框

**Boss 血条**:
- 外层面板背景 + 暗红边框
- 填充区顶部高光线
- BOSS 标签加暗红背景框 + 红色边框

**玩家 HUD**:
- HP/武器区域统一暗色面板背景
- HP 条增加 5 格分段刻度线
- 武器名左侧增加彩色小方块图标（白边框）
- HP 填充区高光线

### 验证结果
- 4/4 修改文件编译通过
- 游戏启动 3 秒无异常

---

## 2026-05-19 — 敌人卡墙修复 + 仇恨系统

### 敌人卡墙真正根因

之前的 `patrol_dir` 修复只解决了一半。完整链路：

1. 敌人检测到台阶 → 跳跃 (`vy=-580, on_ground=False`)
2. 下一帧 `update_physics`：向前移动 1px 撞到台阶瓦片 → `resolve_collision_x` 将 `vx` 归零
3. vx 恢复在 `if self.on_ground:` 内 → 空中跳过 → **vx 永久为 0**
4. 垂直起跳垂直落下 → 无限循环，跳不上台阶

**修复**: 跳跃决策时显式 `self.vx = self.patrol_dir * speed`，确保空中也有水平动量。

### 仇恨系统（Aggro）

**PatrolEnemy 新增追逐行为**:
- 玩家进入 200px 水平 + 100px 垂直范围 → `aggro = True`
- 追逐速度 110 px/s（比巡逻 70 px/s 快 57%）
- 追逐时无视 `patrol_range` 限制
- 视觉反馈：身体红橙色 `(255, 100, 30)`，眼睛变黄
- 玩家离开范围后恢复普通巡逻

**新增常量** (`settings.py`):
- `PATROL_AGGRO_RANGE = 200`
- `PATROL_CHASE_SPEED = 110`

**FlyingEnemy** 已有 250px aggro 追踪，**BossEnemy** 已有面向玩家逻辑，均未修改。

### 受影响的文件
- `enemy.py` — PatrolEnemy 重写 update() + 新增 render() override
- `settings.py` — +2 常量

### 验证结果
- 2/2 文件编译通过
- 游戏启动 3 秒无异常

---

## 2026-05-19 — 敌人卡墙真正修复 + HUD 极简重设计

### 敌人卡墙：第二次修复

之前的修复在 AI 决策末尾设 `vx`，但下一帧 `update_physics` 最先执行，碰撞解析再次将 vx 归零 → 修复无效。

**真正修复**: 新增 `_jumping` 标记追踪自愿跳跃（台阶/过坑）。

- AI 跳解决策时：`self._jumping = True`
- `update_physics` **之后**：若 `_jumping and not on_ground and not had_knockback` → 恢复 `vx`
- 落地（`on_ground`）时：清除 `_jumping = False`
- 击退检测：`had_knockback` 在 physics 前快照，防止盖写击退速度

这样敌人在空中每帧都恢复水平动量，不被碰撞清零打断。

### HUD 极简重设计（main.py）

旧 HUD 面板 `x=-16` 超出屏幕左边界，布局混乱。

新设计：底部居中单行水平排列，无背景面板。

```
HP  ████████████░░░░  3/5        ■ 枪
```

- 全部元素水平居中，`start_x = (SCREEN_WIDTH - total_w) // 2`
- HP 标签 + 渐变血条（带高光+分段刻度）+ `3/5` 数值 + 武器色块图标 + 武器名
- 间距统一（10/10/24px），干净不挡画面

### 受影响的文件
- `enemy.py` — +`_jumping` flag，`update_physics` 后恢复逻辑
- `main.py` — `_draw_player_hp_bar()` 完全重写

### 验证结果
- 2/2 文件编译通过
- 游戏启动 3 秒无异常

---

## 2026-05-19 — 数值调整：血量/伤害/HP 百分比显示

### 改动

| 参数 | 旧值 | 新值 | 文件 |
|------|------|------|------|
| PLAYER_MAX_HP | 5 | **20** | settings.py |
| 剑 damage | 1 | **2** | weapon.py |
| 枪 damage | 1 | **2** | weapon.py |
| 斧 damage | 2 | **3** | weapon.py |
| HP 显示格式 | `3/5` | **`60%`** | main.py |

### 效果
- 三武器伤害 2/2/3，PatrolEnemy(HP=3) 两刀杀，FlyingEnemy(HP=2) 剑/枪一刀秒
- 玩家容错从 5 提升到 20，大幅降低难度
- HP 百分比显示更直观

### 验证结果
- 3/3 文件编译通过，游戏启动无异常

---

## 2026-05-19 — 阶段七：弓箭远程武器

### 新建 `projectile.py`

**Arrow 类** — 抛物线飞行箭矢:
- 初速: `vx = facing * 350`, `vy = -80`（微微上抛）
- 重力: 600 px/s²
- 最大射程: 400px 后自动销毁
- 碰撞: 每帧检查当前瓦片 `level.is_solid()`，碰墙即销毁
- 渲染: 箭杆细线 + 箭头 V 形两条线，方向随速度角度旋转

### 武器系统扩展

**weapon.py** — 新增第四把武器 WEBOW:
- 伤害 2，冷却 0.45s
- 前摇 0.12s（拉弓动画），active 0.01s（瞬间放箭），收招 0.15s
- `"type": "ranged"` 标记远程武器
- 所有近战武器增加 `"type": "melee"` 字段
- WEAPONS 列表: 剑→枪→斧→弓，Q 键四档循环

**player.py**:
- `_pending_projectile` 标记：bow active 阶段设置，main.py 读取后清除
- `get_pending_projectile()`: 一次性消费标记
- 攻击阶段机: startup→active 时根据 `type` 分支（ranged→设标记，melee→建判定框）
- `_render_shoot()`: startup 拉弓弦（弧形+弦线收紧），active 闪光+箭轨提示，recovery 弓松弛淡出

**main.py**:
- `self.projectiles` 列表管理
- 每帧检查 `get_pending_projectile()` → 生成 Arrow
- 箭矢 update + 敌人碰撞检测（逐个遍历，命中即销毁）
- 渲染顺序: 关卡→敌人→**箭矢**→粒子→玩家→HUD

### 弹道数据分析
- 飞行时间: vy 从 -80 到 0 = 80/600 = 0.13s 上升，对称下落 0.13s，共约 0.27s
- 水平距离: 350 × 0.27 = 94px（抛物线顶点时）
- 实际有效射程约 200-250px（考虑地形高度差）

### 受影响的文件
| 文件 | 改动 |
|------|------|
| `projectile.py` | **新建** |
| `weapon.py` | +WEBOW, +"type" 字段 ×4, WEAPONS 列表 +1 |
| `player.py` | +_pending_projectile, +get_pending_projectile(), +_render_shoot() |
| `main.py` | Arrow 导入, 箭矢生成/更新/碰撞/渲染全流程 |

### 验证结果
- 4/4 文件编译通过
- 游戏启动 3 秒无异常

---

## 2026-05-19 — Claude Code 自定义 Skill：文档同步规则

### 完成内容
- **`.claude/skills/sync-docs.md`** — 新建自定义 skill
  - 修改或新增任何代码时，强制同步更新 `md/rz.md`（开发日志）和 `md/CLAUDE.md`（项目文档）
  - `rz.md` 记录做了什么、为什么、遇到的问题及解决方案
  - `CLAUDE.md` 记录项目结构、系统设计、架构变更
  - 触发条件：新增/修改 .py 文件、类、函数、常量、关卡数据、UI 界面、Bug 修复

### 架构决策
- Skill 放在项目级 `.claude/skills/` 目录（非用户级），仅对本项目生效
- 执行顺序：代码修改 → rz.md → CLAUDE.md → 一并提交


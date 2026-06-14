// Status: mock
import type { ResourceType } from '@/lib/sse.types';

export const mockResourceTitle: Record<ResourceType, string> = {
  doc: 'SQL 注入基础讲解文档',
  ppt: 'SQL 注入课堂演示大纲',
  mindmap: 'SQL 注入知识结构图',
  quiz: 'SQL 注入练习题',
  lab: 'SQL 注入实操案例',
  video: 'SQL 注入视频脚本',
  readings: 'SQL 注入拓展阅读',
};

export const mockResourceContent: Record<ResourceType, string> = {
  doc: `# SQL 注入基础讲解

## 学习目标

- 判断输入是否进入 SQL 查询结构
- 区分报错注入、布尔盲注与时间盲注的观察信号
- 使用参数化查询完成最小修复，并说明为什么有效

## 风险来源

SQL 注入的核心风险，是把用户输入错误地拼接进查询语句。攻击者输入的内容不再只是“数据”，而会被数据库解释成语法片段。

| 环节 | 高风险信号 | 推荐处理 |
|---|---|---|
| 登录查询 | 字符串拼接用户名与密码 | 参数化查询 |
| 搜索接口 | 关键词直接进入 WHERE 条件 | 白名单字段 + 绑定变量 |
| 排序字段 | order_by 直接拼接 | 固定枚举映射 |

## 易受攻击写法

\`\`\`python
def vulnerable_login(conn, username, password):
    sql = f"select id from users where name = '{username}' and password = '{password}'"
    return conn.execute(sql).fetchone()
\`\`\`

当用户名输入为 \`admin' --\` 时，后半段密码判断可能被注释掉。

## 修复方式

\`\`\`python
def safe_login(conn, username, password):
    sql = "select id from users where name = ? and password = ?"
    return conn.execute(sql, (username, password)).fetchone()
\`\`\`

参数化查询会把输入作为数据绑定，数据库不会把输入内容重新解释为 SQL 语法。

## 复盘问题

1. 这个接口的输入从哪里进入查询？
2. 是否有动态字段名、排序名等无法直接绑定的位置？
3. 修复后是否覆盖正常登录、错误密码、典型 payload 三组回归用例？`,

  ppt: `# SQL 注入基础
## 从登录接口看输入如何变成风险

- 课程目标：识别、解释、修复
- 演示主线：登录框 → 查询语句 → 参数化查询

---

# 风险来源

- 用户输入被拼进 SQL 字符串
- 数据库把攻击输入当成语法执行
- 常见影响：绕过登录、读取数据、修改数据

---

# 判断流程

1. 找到输入进入查询的位置
2. 观察报错、真假条件、响应时间
3. 记录 payload 与页面差异

---

# 修复方案

- 首选参数化查询
- 动态字段使用白名单映射
- 数据库账号采用最小权限

---

# 课堂练习

- 判断一段登录代码是否存在风险
- 写出参数化查询版本
- 用三组用例验证修复效果`,

  mindmap: `# SQL 注入基础

## 成因

### 输入进入查询

#### 登录参数
#### 搜索关键词
#### 排序字段

### 代码拼接

#### 字符串模板
#### 手写转义

## 判断

### 报错注入

#### 语法错误回显
#### 数据库类型线索

### 布尔盲注

#### 恒真条件
#### 恒假条件

### 时间盲注

#### 延迟函数
#### 响应时间差异

## 防护

### 参数化查询

#### 绑定变量
#### ORM 安全 API

### 最小权限

#### 只读账号
#### 分库分表权限

### 审计

#### 记录异常查询
#### 关联请求日志`,

  quiz: JSON.stringify({
    questions: [
      {
        id: 'q1',
        type: 'single',
        prompt: '下列哪一项最能解释参数化查询降低 SQL 注入风险的原因？',
        options: ['把用户输入作为数据绑定', '自动关闭数据库连接', '隐藏所有错误页面', '把密码改得更复杂'],
        answer: '把用户输入作为数据绑定',
        explanation: '参数化查询让数据库区分语句结构与输入数据，攻击字符串不会再被解释为 SQL 语法。',
      },
      {
        id: 'q2',
        type: 'multiple',
        prompt: '排查 SQL 注入时，哪些现象可以作为观察信号？',
        options: ['报错信息暴露 SQL 语法', '真假条件导致页面差异', '延迟函数造成响应变慢', '图片加载速度变快'],
        answer: ['报错信息暴露 SQL 语法', '真假条件导致页面差异', '延迟函数造成响应变慢'],
        explanation: '报错、布尔差异与时间差异分别对应常见的注入确认路径。',
      },
      {
        id: 'q3',
        type: 'short',
        prompt: '请用一句话说明为什么 order_by 这类动态字段不能直接依赖绑定变量。',
        answer: '动态字段属于语句结构，需要使用白名单映射，而不是把用户输入直接拼接进 SQL。',
        explanation: '绑定变量通常用于值，不适合替代表名、列名、排序方向等 SQL 结构片段。',
      },
    ],
  }, null, 2),

  lab: `# SQL 注入修复实验

## 实验目标

修复一个登录接口中的字符串拼接查询，并用回归用例确认正常登录、错误密码与注入 payload 都按预期处理。

## 步骤

1. 打开 \`backend/auth/login.py\`，定位 \`vulnerable_login\`。
2. 找到用户名和密码进入 SQL 的位置。
3. 将字符串拼接改为参数化查询。
4. 运行回归测试并记录修复前后差异。

## 待修复代码

\`\`\`python
def vulnerable_login(conn, username, password):
    sql = f"select id from users where name = '{username}' and password = '{password}'"
    return conn.execute(sql).fetchone()
\`\`\`

## 推荐修复

\`\`\`python
def safe_login(conn, username, password):
    sql = "select id from users where name = ? and password = ?"
    return conn.execute(sql, (username, password)).fetchone()
\`\`\`

## 验收点

- [ ] 正确账号密码可以登录
- [ ] 错误密码不能登录
- [ ] \`admin' --\` 不能绕过登录
- [ ] 测试日志能说明修复前后差异

## 复制命令

\`\`\`bash
python -m pytest tests/websec/test_sql_injection.py -q
\`\`\``,

  video: JSON.stringify({
    title: 'SQL 注入基础视频脚本',
    tts: '本节课通过登录接口演示 SQL 注入的成因、判断流程与参数化查询修复方法。先看风险输入如何改变查询结构，再用回归测试验证修复效果。',
    scenes: [
      { id: 'S1', scene: '风险开场', narration: '登录框接收用户名和密码，看似普通输入可能改变查询结构。', visual: '展示登录表单与 admin 输入', duration: 18 },
      { id: 'S2', scene: '查询展开', narration: '当代码用字符串拼接 SQL 时，输入会进入语句结构。', visual: '高亮 select 语句中的拼接位置', duration: 26 },
      { id: 'S3', scene: '攻击观察', narration: '使用恒真条件、注释符或延迟函数观察页面差异。', visual: '对比正常请求与 payload 请求', duration: 32 },
      { id: 'S4', scene: '修复验证', narration: '改为参数化查询后，payload 只会作为数据绑定。', visual: '展示测试通过与证据来源', duration: 24 },
    ],
  }, null, 2),

  readings: JSON.stringify({
    groups: [
      {
        platform: 'owasp',
        items: [
          {
            title: 'OWASP SQL Injection 官方说明',
            summary: '适合建立 SQL 注入定义、影响范围与基础防护框架。',
            url: 'https://owasp.org/www-community/attacks/SQL_Injection',
            chunk_id: '00000000-0000-0000-0000-000000000501',
          },
        ],
      },
      {
        platform: 'portswigger',
        items: [
          {
            title: 'PortSwigger SQL Injection 学院专题',
            summary: '适合按实验场景学习报错、联合查询、盲注与防护。',
            url: 'https://portswigger.net/web-security/sql-injection',
            chunk_id: '00000000-0000-0000-0000-000000000502',
          },
        ],
      },
      {
        platform: 'bili',
        items: [
          {
            title: 'SQL 注入课堂演示转写片段',
            summary: '适合快速复盘注入点判断与修复前后对比。',
            url: 'https://www.bilibili.com/video/BV1sql_demo',
            chunk_id: '00000000-0000-0000-0000-000000000503',
          },
        ],
      },
    ],
  }, null, 2),
};

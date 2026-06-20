export type SearchItem = {
  id: string;
  title: string;
  summary?: string;
  url: string;
  category: 'nav' | 'page';
  parent?: string;
};

export const navItems: SearchItem[] = [
  { id: 'nav-workspace', title: '总览', url: '/workspace', category: 'nav' },
  { id: 'nav-practice', title: '实战进阶', url: '/practice?tab=tutorial', category: 'nav' },
  { id: 'nav-course', title: '课程学习', url: '/course', category: 'nav' },
  { id: 'nav-research', title: '科研创新', url: '/research?tab=fund', category: 'nav' },
  { id: 'nav-writing', title: '选题写作', url: '/writing?tab=deduce', category: 'nav' },
  { id: 'nav-chat', title: '智能问答', url: '/chat?tab=topic', category: 'nav' },
  { id: 'nav-forum', title: '交流论坛', url: '/forum?tab=security', category: 'nav' },
  { id: 'nav-careers', title: '就业招聘', url: '/careers?tab=jobs', category: 'nav' },
  { id: 'nav-tasks', title: '计划任务', url: '/tasks?tab=board', category: 'nav' },
  { id: 'nav-profile', title: '个人中心', url: '/profile?tab=persona', category: 'nav' },

  { id: 'nav-workspace-today-course', title: '今日课程', summary: '继续 SQL 注入课程、查看进度和知识点', url: '/workspace#today-course', category: 'nav', parent: '总览' },
  { id: 'nav-workspace-today-tasks', title: '今日任务', summary: '查看今日工作内容、简报和待处理任务', url: '/workspace#today-tasks', category: 'nav', parent: '总览' },
  { id: 'nav-workspace-recent-resources', title: '生成资源', summary: '最近生成的课程资源与质量分', url: '/workspace#recent-resources', category: 'nav', parent: '总览' },
  { id: 'nav-workspace-agent-runs', title: '智能体活动', summary: '最近 course_learning trace 与质量分', url: '/workspace#agent-runs', category: 'nav', parent: '总览' },
  { id: 'nav-workspace-capability', title: '能力画像', summary: '基于 user_capabilities 的能力预览', url: '/workspace#capability', category: 'nav', parent: '总览' },
  { id: 'nav-workspace-rhythm', title: '本周节奏', summary: '本周学习节奏、日程和数据状态', url: '/workspace#rhythm', category: 'nav', parent: '总览' },

  { id: 'nav-practice-tutorial', title: '教程中心', summary: '学习教程和工具使用', url: '/practice?tab=tutorial', category: 'nav', parent: '实战进阶' },
  { id: 'nav-practice-tools', title: '工具库', summary: '安全工具集', url: '/practice?tab=tools', category: 'nav', parent: '实战进阶' },
  { id: 'nav-practice-contest', title: '竞赛专区', summary: 'CTF竞赛和比赛', url: '/practice?tab=contest', category: 'nav', parent: '实战进阶' },
  { id: 'nav-practice-hvv', title: '护网行动', summary: '护网行动相关', url: '/practice?tab=hvv', category: 'nav', parent: '实战进阶' },
  { id: 'nav-practice-range', title: '靶场演练', summary: '在线靶场练习', url: '/practice?tab=range', category: 'nav', parent: '实战进阶' },
  { id: 'nav-practice-cases', title: '实战案例', summary: '真实攻防案例', url: '/practice?tab=cases', category: 'nav', parent: '实战进阶' },
  { id: 'nav-practice-ddl', title: '竞赛DDL', summary: '竞赛截止日期', url: '/practice?tab=ddl', category: 'nav', parent: '实战进阶' },

  { id: 'nav-course-entry', title: '课程入口', summary: '选择课程并构建学习画像', url: '/course?courseId=web-security-foundation&view=structured&tab=entry', category: 'nav', parent: '课程学习' },
  { id: 'nav-course-path', title: '学习路径', summary: '查看 SQL 注入个性化学习路径', url: '/course?courseId=web-security-foundation&view=structured&tab=path', category: 'nav', parent: '课程学习' },
  { id: 'nav-course-workbench', title: '资源工作台', summary: '切换文档、PPT、思维导图、题目、实验、阅读与视频脚本', url: '/course?courseId=web-security-foundation&view=structured&tab=workbench', category: 'nav', parent: '课程学习' },
  { id: 'nav-course-tutor', title: '辅导对话', summary: '进入课程上下文的智能辅导', url: '/course?courseId=web-security-foundation&view=structured&tab=tutor', category: 'nav', parent: '课程学习' },
  { id: 'nav-course-assess', title: '效果评估', summary: '完成答题反馈和能力画像回流', url: '/course?courseId=web-security-foundation&view=structured&tab=assess', category: 'nav', parent: '课程学习' },

  { id: 'nav-research-fund', title: '基金项目', summary: '科研基金项目', url: '/research?tab=fund', category: 'nav', parent: '科研创新' },
  { id: 'nav-research-news', title: '科研动态', summary: '最新科研动态', url: '/research?tab=news', category: 'nav', parent: '科研创新' },
  { id: 'nav-research-innovation', title: '学术创新', summary: '学术创新成果', url: '/research?tab=innovation', category: 'nav', parent: '科研创新' },
  { id: 'nav-research-hot', title: '热点文章', summary: '热点学术文章', url: '/research?tab=hot', category: 'nav', parent: '科研创新' },
  { id: 'nav-research-patent', title: '专利成果', summary: '专利申请和成果', url: '/research?tab=patent', category: 'nav', parent: '科研创新' },
  { id: 'nav-research-lab', title: '开放实验室', summary: '开放实验资源', url: '/research?tab=lab', category: 'nav', parent: '科研创新' },
  { id: 'nav-research-compare', title: '科研机会对比', summary: '科研机会比较', url: '/research?tab=compare', category: 'nav', parent: '科研创新' },

  { id: 'nav-writing-deduce', title: '选题推演', summary: '选题推演分析', url: '/writing?tab=deduce', category: 'nav', parent: '选题写作' },
  { id: 'nav-writing-cards', title: '选题卡池', summary: '选题卡片池', url: '/writing?tab=cards', category: 'nav', parent: '选题写作' },
  { id: 'nav-writing-canvas', title: '创意画布', summary: '创意构思画布', url: '/writing?tab=canvas', category: 'nav', parent: '选题写作' },
  { id: 'nav-writing-module', title: '写作模块', summary: '写作模板模块', url: '/writing?tab=module', category: 'nav', parent: '选题写作' },
  { id: 'nav-writing-proposal', title: '计划书生成', summary: '计划书自动生成', url: '/writing?tab=proposal', category: 'nav', parent: '选题写作' },
  { id: 'nav-writing-editor', title: '文档编辑', summary: '在线文档编辑', url: '/writing?tab=editor', category: 'nav', parent: '选题写作' },
  { id: 'nav-writing-ppt', title: 'PPT大纲', summary: 'PPT大纲生成', url: '/writing?tab=ppt', category: 'nav', parent: '选题写作' },
  { id: 'nav-writing-cite', title: '引用证据', summary: '引用证据管理', url: '/writing?tab=cite', category: 'nav', parent: '选题写作' },

  { id: 'nav-chat-topic', title: '选题指导', summary: '选题相关指导', url: '/chat?tab=topic', category: 'nav', parent: '智能问答' },
  { id: 'nav-chat-research', title: '科研咨询', summary: '科研相关咨询', url: '/chat?tab=research', category: 'nav', parent: '智能问答' },
  { id: 'nav-chat-contest', title: '竞赛咨询', summary: '竞赛相关咨询', url: '/chat?tab=contest', category: 'nav', parent: '智能问答' },
  { id: 'nav-chat-policy', title: '政策解读', summary: '政策解读服务', url: '/chat?tab=policy', category: 'nav', parent: '智能问答' },
  { id: 'nav-chat-hot', title: '热点研判', summary: '热点分析研判', url: '/chat?tab=hot', category: 'nav', parent: '智能问答' },
  { id: 'nav-chat-writing', title: '写作辅导', summary: '写作辅助指导', url: '/chat?tab=writing', category: 'nav', parent: '智能问答' },
  { id: 'nav-chat-path', title: '路径建议', summary: '学习路径建议', url: '/chat?tab=path', category: 'nav', parent: '智能问答' },

  { id: 'nav-forum-security', title: '安全论坛', summary: '安全技术论坛', url: '/forum?tab=security', category: 'nav', parent: '交流论坛' },
  { id: 'nav-forum-topic', title: '话题讨论', summary: '热门话题讨论', url: '/forum?tab=topic', category: 'nav', parent: '交流论坛' },
  { id: 'nav-forum-team', title: '项目组队', summary: '项目组队协作', url: '/forum?tab=team', category: 'nav', parent: '交流论坛' },
  { id: 'nav-forum-exp', title: '经验分享', summary: '经验分享交流', url: '/forum?tab=exp', category: 'nav', parent: '交流论坛' },
  { id: 'nav-forum-qa', title: '问答互助', summary: '问答互助社区', url: '/forum?tab=qa', category: 'nav', parent: '交流论坛' },
  { id: 'nav-forum-notice', title: '活动公告', summary: '论坛活动公告', url: '/forum?tab=notice', category: 'nav', parent: '交流论坛' },
  { id: 'nav-forum-exchange', title: '资源交换', summary: '资源共享交换', url: '/forum?tab=exchange', category: 'nav', parent: '交流论坛' },

  { id: 'nav-careers-jobs', title: '招聘速递', summary: '招聘信息速递', url: '/careers?tab=jobs', category: 'nav', parent: '就业招聘' },
  { id: 'nav-careers-analysis', title: '岗位分析', summary: '岗位分析报告', url: '/careers?tab=analysis', category: 'nav', parent: '就业招聘' },
  { id: 'nav-careers-gap', title: '技能差距', summary: '技能差距分析', url: '/careers?tab=gap', category: 'nav', parent: '就业招聘' },
  { id: 'nav-careers-path', title: '学习路径', summary: '学习路径规划', url: '/careers?tab=path', category: 'nav', parent: '就业招聘' },
  { id: 'nav-careers-resume', title: '简历优化', summary: '简历优化建议', url: '/careers?tab=resume', category: 'nav', parent: '就业招聘' },
  { id: 'nav-careers-interview', title: '面试题库', summary: '面试题目库', url: '/careers?tab=interview', category: 'nav', parent: '就业招聘' },
  { id: 'nav-careers-company', title: '企业画像', summary: '企业信息画像', url: '/careers?tab=company', category: 'nav', parent: '就业招聘' },
  { id: 'nav-careers-direction', title: '发展方向规划', summary: '职业发展方向', url: '/careers?tab=direction', category: 'nav', parent: '就业招聘' },

  { id: 'nav-tasks-board', title: '看板视图', summary: '看板任务视图', url: '/tasks?tab=board', category: 'nav', parent: '计划任务' },
  { id: 'nav-tasks-timeline', title: '时间线', summary: '任务时间线', url: '/tasks?tab=timeline', category: 'nav', parent: '计划任务' },
  { id: 'nav-tasks-list', title: '清单管理', summary: '任务清单管理', url: '/tasks?tab=list', category: 'nav', parent: '计划任务' },
  { id: 'nav-tasks-milestone', title: '里程碑', summary: '项目里程碑', url: '/tasks?tab=milestone', category: 'nav', parent: '计划任务' },
  { id: 'nav-tasks-calendar', title: '截止日历', summary: '截止日期日历', url: '/tasks?tab=calendar', category: 'nav', parent: '计划任务' },
  { id: 'nav-tasks-team', title: '协作分工', summary: '团队协作分工', url: '/tasks?tab=team', category: 'nav', parent: '计划任务' },

  { id: 'nav-profile-persona', title: '用户画像', summary: '个人用户画像', url: '/profile?tab=persona', category: 'nav', parent: '个人中心' },
  { id: 'nav-profile-vault', title: '个人资产库', summary: '个人资产存储', url: '/profile?tab=vault', category: 'nav', parent: '个人中心' },
  { id: 'nav-profile-docs', title: '文档资产', summary: '个人文档资产', url: '/profile?tab=docs', category: 'nav', parent: '个人中心' },
  { id: 'nav-profile-slides', title: '演示资产', summary: '演示文稿资产', url: '/profile?tab=slides', category: 'nav', parent: '个人中心' },
  { id: 'nav-profile-code', title: '代码资产', summary: '代码资产管理', url: '/profile?tab=code', category: 'nav', parent: '个人中心' },
  { id: 'nav-profile-proof', title: '证明材料', summary: '证明材料管理', url: '/profile?tab=proof', category: 'nav', parent: '个人中心' },
  { id: 'nav-profile-submit', title: '提交清单', summary: '提交清单管理', url: '/profile?tab=submit', category: 'nav', parent: '个人中心' },
  { id: 'nav-profile-notice', title: '通知设置', summary: '通知偏好设置', url: '/profile?tab=notice', category: 'nav', parent: '个人中心' },
  { id: 'nav-profile-account', title: '账户与合规', summary: '账户和合规设置', url: '/profile?tab=account', category: 'nav', parent: '个人中心' },
];

export const pageItems: SearchItem[] = [
  { id: 'page-workspace', title: '工作台', summary: '今日要务、截止提醒、推荐行动、最近生成物', url: '/workspace', category: 'page' },
  { id: 'page-practice', title: '实战进阶', summary: '教程中心、工具库、竞赛专区', url: '/practice', category: 'page' },
  { id: 'page-course', title: '课程学习', summary: '画像、路径、资源工作台、辅导对话、效果评估', url: '/course', category: 'page' },
  { id: 'page-research', title: '科研创新', summary: '基金项目、科研动态、学术创新、热点文章', url: '/research', category: 'page' },
  { id: 'page-writing', title: '选题写作', summary: '选题推演、写作模块、文档编辑、PPT大纲', url: '/writing', category: 'page' },
  { id: 'page-chat', title: '智能问答', summary: '选题指导、科研咨询、竞赛咨询', url: '/chat', category: 'page' },
  { id: 'page-forum', title: '交流论坛', summary: '安全论坛、话题讨论、问答互助', url: '/forum', category: 'page' },
  { id: 'page-careers', title: '就业招聘', summary: '招聘速递、岗位分析、简历优化', url: '/careers', category: 'page' },
  { id: 'page-tasks', title: '计划任务', summary: '看板视图、时间线、里程碑', url: '/tasks', category: 'page' },
  { id: 'page-profile', title: '个人中心', summary: '用户画像、个人资产库、账户设置', url: '/profile', category: 'page' },
];

export const allSearchItems: SearchItem[] = [...navItems, ...pageItems];

export function searchItems(query: string): SearchItem[] {
  if (!query.trim()) return [];
  const lower = query.toLowerCase();
  return allSearchItems.filter(item =>
    item.title.toLowerCase().includes(lower) ||
    (item.summary && item.summary.toLowerCase().includes(lower)) ||
    (item.parent && item.parent.toLowerCase().includes(lower))
  );
}

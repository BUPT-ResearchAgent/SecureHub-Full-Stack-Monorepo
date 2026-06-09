import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useScroll, useTransform, useSpring } from 'motion/react';
import {
  ArrowRight,
  Sparkles,
  TrendingUp,
  FileText,
  Target,
  Calendar,
  FolderOpen,
  ChevronDown,
  Play,
  CheckCircle2,
  Shield,
  Users,
  Award,
  Briefcase,
  BookOpen,
  Trophy,
} from 'lucide-react';
import { DataTag } from '@/app/components/DataTag';
import { useAuth } from '@/app/features/auth/store';

export function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);
  const heroRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  });

  const y = useTransform(scrollYProgress, [0, 1], [0, 100]);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0.3]);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const enterWorkspace = () => {
    navigate(isAuthenticated ? '/workspace' : '/login?redirect=/workspace');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">安</span>
            </div>
            <span className="font-semibold text-gray-900">安枢智梯 CyberLadder</span>
          </div>

          <div className="hidden md:flex items-center gap-8">
            <button
              onClick={() => scrollToSection('features')}
              className="text-sm text-gray-700 hover:text-gray-900 transition-colors"
            >
              产品能力
            </button>
            <button
              onClick={() => scrollToSection('workflow')}
              className="text-sm text-gray-700 hover:text-gray-900 transition-colors"
            >
              工作流程
            </button>
            <button
              onClick={() => scrollToSection('evidence')}
              className="text-sm text-gray-700 hover:text-gray-900 transition-colors"
            >
              证据链
            </button>
            <button
              onClick={() => scrollToSection('outputs')}
              className="text-sm text-gray-700 hover:text-gray-900 transition-colors"
            >
              模板与产出
            </button>
            <button
              onClick={() => scrollToSection('faq')}
              className="text-sm text-gray-700 hover:text-gray-900 transition-colors"
            >
              FAQ
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => scrollToSection('preview')}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200"
            >
              查看演示
            </button>
            <button
              onClick={enterWorkspace}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-blue-600 hover:bg-brand-blue-700 rounded-lg transition-colors flex items-center gap-2"
            >
              进入工作台
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section ref={heroRef} className="relative pt-32 pb-20 px-6 overflow-hidden">
        <motion.div style={{ y, opacity }} className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="space-y-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
              >
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-brand-blue-50 text-brand-blue-700 rounded-full text-sm font-medium mb-6">
                  <Sparkles className="w-4 h-4" />
                  面向网安学生的科研与竞赛智能体
                </div>
                <h1 className="text-5xl font-bold text-gray-900 leading-tight mb-6">
                  把网安情报
                  <br />
                  变成可执行计划
                </h1>
                <p className="text-xl text-gray-600 leading-relaxed">
                  基于招聘需求、政策标准、热点趋势与竞赛信息，为学生团队生成选题、计划书与交付清单。
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="flex items-center gap-4"
              >
                <button
                  onClick={enterWorkspace}
                  className="px-6 py-3 text-base font-medium text-white bg-brand-blue-600 hover:bg-brand-blue-700 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-brand-blue-600/20"
                >
                  进入工作台
                  <ArrowRight className="w-5 h-5" />
                </button>
                <button
                  onClick={() => scrollToSection('preview')}
                  className="px-6 py-3 text-base font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200 flex items-center gap-2"
                >
                  <Play className="w-5 h-5" />
                  查看产品预览
                </button>
              </motion.div>

              {/* Stats */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="grid grid-cols-3 gap-6 pt-8 border-t border-gray-200"
              >
                <div>
                  <div className="text-2xl font-bold text-gray-900">1,099+</div>
                  <div className="text-sm text-gray-600 mt-1">数据源</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-900">7类</div>
                  <div className="text-sm text-gray-600 mt-1">情报类型</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-900">94%</div>
                  <div className="text-sm text-gray-600 mt-1">覆盖度</div>
                </div>
              </motion.div>
            </div>

            {/* Right - Product Preview with Animation */}
            <motion.div
              initial={{
                opacity: 0,
                y: -120,
                rotateX: 6,
                rotateY: -10,
                scale: 0.92,
              }}
              animate={{
                opacity: 1,
                y: 0,
                rotateX: 0,
                rotateY: 0,
                scale: 1,
              }}
              transition={{
                type: 'spring',
                stiffness: 80,
                damping: 20,
                duration: 1.2,
              }}
              whileHover={{
                scale: 1.02,
                rotateY: 2,
                rotateX: -2,
              }}
              id="preview"
              className="relative"
              style={{ perspective: '2000px' }}
            >
              <div className="relative bg-white rounded-xl shadow-2xl overflow-hidden border border-gray-200">
                {/* Browser Chrome */}
                <div className="bg-gray-100 border-b border-gray-200 px-4 py-3 flex items-center gap-2">
                  <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-400"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                    <div className="w-3 h-3 rounded-full bg-green-400"></div>
                  </div>
                  <div className="flex-1 ml-4">
                    <div className="bg-white border border-gray-200 rounded-md px-3 py-1 text-xs text-gray-500">
                      securehub.app/dashboard
                    </div>
                  </div>
                </div>

                {/* Dashboard Preview */}
                <div className="bg-gradient-to-br from-gray-50 to-white p-6">
                  <div className="space-y-4">
                    {/* Mini Dashboard Header */}
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="h-6 w-32 bg-gray-900 rounded"></div>
                        <div className="h-3 w-48 bg-gray-300 rounded mt-2"></div>
                      </div>
                      <div className="flex gap-2">
                        <div className="h-8 w-20 bg-brand-blue-600 rounded-lg"></div>
                        <div className="h-8 w-20 bg-gray-200 rounded-lg"></div>
                      </div>
                    </div>

                    {/* Mini Cards Grid */}
                    <div className="grid grid-cols-3 gap-3">
                      {[1, 2, 3].map((i) => (
                        <div
                          key={i}
                          className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm"
                        >
                          <div className="h-3 w-16 bg-gray-300 rounded mb-2"></div>
                          <div className="h-6 w-12 bg-gray-900 rounded mb-1"></div>
                          <div className="h-2 w-20 bg-green-400 rounded"></div>
                        </div>
                      ))}
                    </div>

                    {/* Mini Task List */}
                    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="flex items-center gap-3">
                          <div className="w-4 h-4 rounded bg-gray-200"></div>
                          <div className="flex-1 h-3 bg-gray-300 rounded"></div>
                          <div className="h-5 w-12 bg-brand-blue-100 rounded"></div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Glow Effect */}
              <div className="absolute -inset-4 bg-gradient-to-r from-brand-blue-600/20 to-purple-600/20 rounded-3xl blur-3xl -z-10"></div>
            </motion.div>
          </div>
        </motion.div>

        {/* Scroll Indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <div className="flex flex-col items-center gap-2 text-gray-400">
            <span className="text-xs">向下滚动探索更多</span>
            <ChevronDown className="w-5 h-5 animate-bounce" />
          </div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">产品能力</h2>
            <p className="text-lg text-gray-600">
              七类数据驱动，六大核心模块，全流程覆盖
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: TrendingUp,
                title: '机会情报',
                desc: '竞赛与基金截止、对比决策',
                tags: ['D5', 'D7'],
                color: 'brand-blue',
              },
              {
                icon: Target,
                title: '方向推荐',
                desc: '趋势+政策+招聘驱动',
                tags: ['D1', 'D2', 'D4'],
                color: 'purple',
              },
              {
                icon: Sparkles,
                title: '选题推演',
                desc: '画布式推演与风险提示',
                tags: ['D2', 'D4', 'D7'],
                color: 'green',
              },
              {
                icon: FileText,
                title: '写作生成',
                desc: '计划书/PPT/作品本一键生成',
                tags: ['D6', 'D5', 'D2'],
                color: 'orange',
              },
              {
                icon: Calendar,
                title: '计划与任务',
                desc: 'Kanban/里程碑/提交清单',
                tags: ['D5', 'D6'],
                color: 'red',
              },
              {
                icon: FolderOpen,
                title: '成果资产库',
                desc: '版本化沉淀与导出',
                tags: ['D6'],
                color: 'cyan',
              },
            ].map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg hover:border-brand-blue-600 transition-all group"
              >
                <div className="w-12 h-12 bg-brand-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-brand-blue-600 transition-colors">
                  <feature.icon className="w-6 h-6 text-brand-blue-600 group-hover:text-white transition-colors" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-gray-600 mb-4">{feature.desc}</p>
                <div className="flex gap-2">
                  {feature.tags.map((tag) => (
                    <DataTag key={tag} type={tag as any} />
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow Section */}
      <section id="workflow" className="py-20 px-6 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">工作流程</h2>
            <p className="text-lg text-gray-600">从情报到交付，四步闭环</p>
          </div>

          <div className="relative">
            {/* Timeline Line */}
            <div className="absolute top-8 left-0 right-0 h-0.5 bg-gray-200 hidden lg:block"></div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative">
              {[
                {
                  step: '01',
                  title: '选方向',
                  desc: '基于招聘与政策推荐研究方向',
                  icon: Target,
                },
                {
                  step: '02',
                  title: '选机会',
                  desc: '对比竞赛与基金项目',
                  icon: TrendingUp,
                },
                {
                  step: '03',
                  title: '推演选题',
                  desc: '画布式选题与风险评估',
                  icon: Sparkles,
                },
                {
                  step: '04',
                  title: '生成文档',
                  desc: '一键生成计划书并进入任务',
                  icon: FileText,
                },
              ].map((step, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.15 }}
                  className="relative"
                >
                  <div className="bg-white border border-gray-200 rounded-xl p-6 text-center">
                    <div className="w-16 h-16 bg-brand-blue-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
                      <step.icon className="w-8 h-8 text-white" />
                    </div>
                    <div className="text-sm font-bold text-brand-blue-600 mb-2">
                      STEP {step.step}
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {step.title}
                    </h3>
                    <p className="text-sm text-gray-600">{step.desc}</p>
                  </div>
                  {index < 3 && (
                    <div className="hidden lg:block absolute top-8 -right-3 w-6 h-6">
                      <ArrowRight className="w-6 h-6 text-brand-blue-600" />
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Evidence Section */}
      <section id="evidence" className="py-20 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left - Explanation */}
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                证据链：可信解释
              </h2>
              <p className="text-lg text-gray-600 mb-6">
                每条推荐都可追溯到数据来源：招聘、政策、热点、趋势、竞赛、模板与基金。
              </p>
              <div className="space-y-4">
                {[
                  {
                    icon: Shield,
                    title: '数据可追溯',
                    desc: '每个推荐都标注数据来源标签',
                  },
                  {
                    icon: CheckCircle2,
                    title: '证据链完整',
                    desc: '支持查看完整引用与摘要',
                  },
                  {
                    icon: BookOpen,
                    title: '智能解释',
                    desc: 'AI生成推荐理由与风险提示',
                  },
                ].map((item, index) => (
                  <div key={index} className="flex gap-4">
                    <div className="w-10 h-10 bg-brand-blue-50 rounded-lg flex items-center justify-center shrink-0">
                      <item.icon className="w-5 h-5 text-brand-blue-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-1">
                        {item.title}
                      </h4>
                      <p className="text-sm text-gray-600">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right - Evidence Drawer Demo */}
            <div className="relative">
              <div className="bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
                <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
                  <h4 className="text-sm font-semibold text-gray-900">
                    证据抽屉
                  </h4>
                </div>
                <div className="p-4 space-y-3">
                  {[
                    { tag: 'D1', title: '网络安全工程师岗位需求增长32%', source: '智联招聘' },
                    { tag: 'D2', title: '《网络安全法》修订草案发布', source: '工信部' },
                    { tag: 'D4', title: '零信任架构成为年度热点', source: 'Gartner' },
                  ].map((evidence, index) => (
                    <div
                      key={index}
                      className="bg-gray-50 border border-gray-200 rounded-lg p-3"
                    >
                      <div className="flex items-start gap-3">
                        <DataTag type={evidence.tag as any} />
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-900 mb-1">
                            {evidence.title}
                          </div>
                          <div className="text-xs text-gray-500">
                            来源：{evidence.source}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Outputs Section */}
      <section id="outputs" className="py-20 px-6 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              模板与产出
            </h2>
            <p className="text-lg text-gray-600">
              一键生成专业文档，支持编辑与导出
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: FileText,
                title: '挑战杯计划书',
                desc: '结构化大纲，可编辑导出',
                badge: 'DOCX',
              },
              {
                icon: Sparkles,
                title: 'PPT 结构',
                desc: '带故事线的演示文稿',
                badge: 'PPTX',
              },
              {
                icon: CheckCircle2,
                title: '提交清单',
                desc: '按节点自动生成',
                badge: 'PDF',
              },
              {
                icon: FolderOpen,
                title: '资产库',
                desc: '版本化记录与管理',
                badge: 'ALL',
              },
            ].map((output, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-all"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-brand-blue-50 rounded-lg flex items-center justify-center">
                    <output.icon className="w-6 h-6 text-brand-blue-600" />
                  </div>
                  <span className="text-xs font-bold text-brand-blue-600 bg-brand-blue-50 px-2 py-1 rounded">
                    {output.badge}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {output.title}
                </h3>
                <p className="text-sm text-gray-600">{output.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">适用对象</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: Users,
                title: '学生团队试点',
                desc: '面向网安专业学生团队',
              },
              {
                icon: Briefcase,
                title: '校内课程推广',
                desc: '辅助科研训练课程教学',
              },
              {
                icon: Trophy,
                title: '面向挑战杯',
                desc: '专为竞赛项目优化流程',
              },
            ].map((item, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-brand-blue-50 to-white border border-brand-blue-100 rounded-xl p-6 text-center"
              >
                <div className="w-16 h-16 bg-brand-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <item.icon className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-20 px-6 bg-gray-50">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              常见问题
            </h2>
          </div>

          <div className="space-y-4">
            {[
              {
                question: '我们需要准备哪些数据？',
                answer:
                  '无需准备数据。系统已内置招聘、政策、热点、趋势、竞赛、模板与基金7类数据源，共1,099+条数据，覆盖度94%。您只需输入研究兴趣或关键词，系统会自动匹配相关情报。',
              },
              {
                question: '推荐是否可解释？',
                answer:
                  '是的。每条推荐都带有完整的证据链，标注数据来源标签（D1-D7），您可以点击查看原始引用、摘要与推荐理由。系统还会提供风险提示与可行性评估。',
              },
              {
                question: '文档是否可导出？',
                answer:
                  '支持。计划书、PPT结构、提交清单等文档均支持导出为DOCX、PPTX、PDF格式，并且可以在线编辑。资产库支持版本化管理，可随时回溯历史版本。',
              },
              {
                question: '适合哪些阶段学生？',
                answer:
                  '主要面向本科高年级与研究生阶段的网安专业学生，适用于挑战杯、科研训练、创新创业项目等场景。团队协作功能支持3-5人小组共同使用。',
              },
            ].map((faq, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-xl overflow-hidden"
              >
                <button
                  onClick={() =>
                    setExpandedFaq(expandedFaq === index ? null : index)
                  }
                  className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
                >
                  <span className="font-semibold text-gray-900">
                    {faq.question}
                  </span>
                  <ChevronDown
                    className={`w-5 h-5 text-gray-400 transition-transform ${
                      expandedFaq === index ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {expandedFaq === index && (
                  <div className="px-6 pb-4 text-sm text-gray-600 leading-relaxed">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6 bg-gradient-to-r from-brand-blue-600 to-brand-blue-700">
        <div className="max-w-4xl mx-auto text-center text-white">
          <h2 className="text-4xl font-bold mb-4">准备好开始了吗？</h2>
          <p className="text-xl mb-8 text-brand-blue-50">
            立即体验智能化的科研与竞赛工作流程
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={enterWorkspace}
              className="px-8 py-4 text-lg font-medium text-brand-blue-600 bg-white hover:bg-gray-50 rounded-lg transition-colors shadow-lg"
            >
              进入工作台
            </button>
            <button
              onClick={() => scrollToSection('features')}
              className="px-8 py-4 text-lg font-medium text-white border-2 border-white hover:bg-white/10 rounded-lg transition-colors"
            >
              了解更多
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div className="col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-brand-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">安</span>
                </div>
                <span className="font-semibold text-white">
                  安枢智梯 CyberLadder
                </span>
              </div>
              <p className="text-sm leading-relaxed">
                面向网安学生的科研与竞赛智能体平台
                <br />
                把网安情报变成可执行计划
              </p>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-3">产品</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <button
                    onClick={() => scrollToSection('features')}
                    className="hover:text-white transition-colors"
                  >
                    产品能力
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => scrollToSection('workflow')}
                    className="hover:text-white transition-colors"
                  >
                    工作流程
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => scrollToSection('outputs')}
                    className="hover:text-white transition-colors"
                  >
                    模板与产出
                  </button>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-3">支持</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <button
                    onClick={() => scrollToSection('faq')}
                    className="hover:text-white transition-colors"
                  >
                    FAQ
                  </button>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition-colors">
                    GitHub
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition-colors">
                    联系我们
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-sm">
              © 2026 安枢智梯 CyberLadder. 挑战杯项目展示原型.
            </div>
            <div className="flex gap-6 text-sm">
              <a href="#" className="hover:text-white transition-colors">
                隐私政策
              </a>
              <a href="#" className="hover:text-white transition-colors">
                使用条款
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

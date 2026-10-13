# 1010 v3 方法图源文件

七张图对应论文图1-1、1-2、2-1、3-1、3-2、4-1、4-2。SVG保留可编辑文字和矢量线条；PDF嵌入字体；PNG为600 dpi，供Word排版。Word内插入的是PNG，不能将其当作可逐节点编辑的Word形状。

所有图均为既有方法的说明示意。图书馆片段为人为构造，不是真实语料或运行案例；图示不证明增强有效、局部策略优于全局或两阶段互补。原四张定量结果图不在此重绘包内，其内容保持不变。

使用Python 3.12、matplotlib 3.11.2绘图，字体为Arial Unicode MS。复现方式：安装requirements.txt中的依赖，在macOS上确保系统补充字体中的Arial Unicode.ttf可用，再运行python draw_figures.py。其他系统应将源码FONT指向可覆盖中文的本地TrueType字体，重新渲染并复核布局。qa_tools中的面板对齐工具由绘图脚本调用；每张图均为单轴连续机制图，因此记录为不适用。

颜色和线型：蓝色为训练路径，青绿色为推理路径，灰色为既有模块、固定对象或上下文，橙色为监督条件或接受门。流程中的实线为数据／表示，虚线为监督／控制；论辩关系图中的Support箭头另有直接标签，NONE不绘成已输出边。

文件清单：figures目录含7组SVG、PDF和PNG；draw_figures.py为源代码；figure_contract.md给出逐图语义与尺寸；figure_qa.json记录字号、碰撞及语义核对；requirements.txt和qa_tools支持复现。具体实验未决事项请看论文附带的修订说明。

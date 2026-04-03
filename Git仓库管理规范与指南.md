# CoPaw 二次开发 Git 仓库管理规范与指南

本文档旨在规范基于 [agentscope-ai/CoPaw](https://github.com/agentscope-ai/CoPaw) 开源仓库进行二次开发时的 Git 仓库管理流程，确保二次开发代码独立可维护、官方新功能可稳定同步，避免代码冲突、版本混乱等问题，适用于所有参与本项目二次开发的人员。

核心目标：实现「二次开发代码安全独立」与「官方更新高效同步」的双向兼容，保障项目长期可维护性。

# 一、核心概念定义

- **上游仓库（upstream）**：指 CoPaw 官方开源仓库，地址为 https://github.com/agentscope-ai/CoPaw.git，是官方新功能、Bug 修复的源头。

- **本地仓库**：开发人员本地电脑上的代码仓库，用于日常开发、代码提交和版本管理。

- **远程仓库（origin）**：开发人员个人/团队的 Git 远程仓库（如 GitHub、GitLab 仓库），用于备份本地开发代码、协同开发，是本地仓库的远程镜像。

- **主分支（main/master）**：用于同步上游仓库官方最新代码，保持与官方版本一致，**禁止在此分支直接编写或修改代码**。

- **开发分支（dev）**：二次开发的核心分支，所有二次开发功能、Bug 修复均在此分支进行，是日常开发的主要分支。

- **功能分支（feature/xxx，可选）**：针对单一新功能或优化的临时分支，开发完成后合并至 dev 分支，适用于多功能并行开发场景。

# 二、仓库初始化（仅执行一次）

初始化操作用于搭建本地仓库、远程仓库与上游官方仓库的关联，确保后续同步和开发流程正常运行。

## 2.1 Fork 官方仓库

1. 访问 CoPaw 官方仓库：https://github.com/agentscope-ai/CoPaw

2. 点击页面右上角「Fork」按钮，将官方仓库复制到个人/团队的 Git 账号下，生成自己的远程仓库（origin）。

## 2.2 克隆远程仓库到本地

打开终端，执行以下命令，将自己 Fork 后的远程仓库克隆到本地（替换命令中的「你的账号」为实际 Git 账号名）：

```bash
git clone https://github.com/你的账号/CoPaw.git
cd CoPaw
```

## 2.3 关联上游官方仓库

在本地仓库目录下，执行以下命令，将官方仓库绑定为「上游源」（upstream），用于后续拉取官方最新代码：

```bash
git remote add upstream https://github.com/agentscope-ai/CoPaw.git
```

验证关联是否成功，执行以下命令：

```bash
git remote -v
```

若输出结果包含以下内容，说明关联成功：

- origin: https://github.com/你的账号/CoPaw.git（fetch/push）

- upstream: https://github.com/agentscope-ai/CoPaw.git（fetch/push）

## 2.4 创建开发分支（dev）

初始化本地仓库后，从 main 分支创建 dev 分支，作为日常开发分支：

```bash
git checkout main
git checkout -b dev
```

将创建的 dev 分支推送到远程仓库（origin），完成分支初始化：

```bash
git push -u origin dev
```

# 三、分支管理规范

分支管理是保障代码整洁、避免冲突的核心，所有开发人员必须严格遵循以下分支使用规则。

## 3.1 分支用途明确

|分支名称|核心用途|操作规范|
|---|---|---|
|main/master|同步上游官方最新代码，作为基准版本|仅用于拉取上游更新、推送备份，禁止直接修改代码|
|dev|二次开发主分支，整合所有二次开发功能|日常开发、功能合并、同步官方更新，可提交代码|
|feature/xxx|单一功能/优化的临时开发分支（可选）|从 dev 分支创建，开发完成后合并回 dev 分支，完成后可删除|
## 3.2 分支命名规范

- 功能分支：feature/功能名称（小写，用连字符分隔），例：feature/add-custom-api

- Bug 修复分支：fix/问题描述（小写，用连字符分隔），例：fix/login-error

- 临时分支：temp/用途-日期，例：temp/test-20260402（仅用于临时测试，不长期保留）

# 四、日常开发流程

所有二次开发工作均在 dev 分支（或 feature 分支）进行，严格遵循以下流程，确保代码可追溯、可回滚。

## 4.1 切换到开发分支

每次开始开发前，确保当前处于 dev 分支（若使用 feature 分支，需先切换到 feature 分支）：

```bash
# 切换到 dev 分支
git checkout dev

# 若使用 feature 分支，从 dev 分支创建并切换
git checkout dev
git checkout -b feature/xxx
```

## 4.2 代码开发与提交

1. 进行代码开发，完成功能或修复后，查看修改内容：

2. 将修改的文件添加到暂存区：

3. 提交代码，提交信息需清晰、规范，格式为「类型: 描述」：

4. 将本地提交推送到远程仓库（origin）对应的分支：

## 4.3 功能分支合并（可选）

若使用 feature 分支开发，功能完成后需合并到 dev 分支：

```bash
# 切换到 dev 分支并拉取最新代码
git checkout dev
git pull origin dev

# 合并 feature 分支到 dev 分支
git merge feature/xxx

# 解决冲突（若有），然后提交并推送
git add .
git commit -m "merge: 合并feature/xxx功能到dev分支"
git push origin dev

# 功能合并完成后，可删除 feature 分支（本地+远程）
git branch -d feature/xxx
git push origin --delete feature/xxx
```

# 五、官方新功能同步流程（每周固定执行）

为确保二次开发版本同步官方最新功能和 Bug 修复，每周固定时间（建议每周一）执行以下同步操作，同步过程中若出现冲突，需妥善处理。

## 5.1 同步官方更新到 main 分支

```bash
# 1. 切换到 main 分支
git checkout main

# 2. 拉取上游官方最新代码（同步官方更新）
git pull upstream main

# 3. 将同步后的 main 分支推送到自己的远程仓库（备份）
git push origin main
```

## 5.2 将官方更新合并到开发分支（dev）

```bash
# 1. 切换到 dev 分支
git checkout dev

# 2. 将 main 分支的官方更新合并到 dev 分支
git merge main

# 3. 处理冲突（关键步骤）
# 若出现冲突，终端会提示冲突文件，打开冲突文件，根据需求修改：
# - <<<<<<< HEAD 下方是本地 dev 分支的代码
# - ======= 下方是官方 main 分支的代码
# - >>>>>>> main
# 修改后保存文件，执行以下命令
git add .
git commit -m "merge: 同步上游官方最新更新（日期：20260402）"

# 4. 将合并后的 dev 分支推送到远程仓库
git push origin dev
```

## 5.3 冲突处理规范

- 冲突处理原则：优先保留二次开发核心逻辑，同时兼容官方更新的合理改动，避免因冲突导致功能异常。

- 若冲突文件是二次开发未修改的官方文件，直接保留官方代码即可。

- 若冲突文件是二次开发修改过的文件，对比本地代码和官方代码，保留需要的逻辑，删除冲突标记（<<<<<<<、=======、>>>>>>>）。

- 冲突处理完成后，需测试相关功能，确保无异常后再提交。

# 六、常用命令速查表

整理日常开发和同步更新常用命令，方便快速查阅使用。

```bash
# 查看远程仓库关联
git remote -v

# 拉取上游官方更新到 main 分支
git checkout main && git pull upstream main && git push origin main

# 合并官方更新到 dev 分支
git checkout dev && git merge main && git add . && git commit -m "merge: 同步官方更新" && git push origin dev

# 查看分支列表
git branch -a

# 切换分支
git checkout 分支名

# 创建并切换分支
git checkout -b 分支名

# 提交代码
git add . && git commit -m "类型: 描述" && git push origin 分支名

# 拉取远程分支最新代码
git pull origin 分支名
```

# 七、注意事项

- 严禁在 main 分支直接编写、修改代码，main 分支仅用于同步官方更新和备份，违规操作可能导致代码混乱、无法同步官方更新。

- 每次提交代码前，务必查看修改内容（git status），避免提交无关文件（如编译产物、日志文件等），建议在项目根目录添加 .gitignore 文件过滤无关文件。

- 同步官方更新时，务必先切换到 main 分支，再拉取上游代码，避免直接在 dev 分支拉取上游代码导致分支混乱。

- 冲突处理后，必须进行功能测试，确保冲突修改未影响原有功能和官方新功能的正常使用。

- 若多人协同开发，需提前沟通开发内容，避免同时修改同一文件导致严重冲突；建议每人负责不同模块，或使用 feature 分支并行开发。

- 定期备份本地仓库和远程仓库，避免因电脑故障、误操作导致代码丢失。

# 八、附则

1. 本文档将根据项目开发需求和 Git 管理经验，适时更新优化，确保规范的适用性。

2. 所有参与本项目二次开发的人员，均需严格遵守本文档规定，若因违规操作导致代码问题，需负责相应的修复工作。

3. 若在使用过程中遇到问题，可参考 Git 官方文档，或咨询项目负责人。

4. 文档版本：v1.0（2026.04.02）
> （注：文档部分内容可能由 AI 生成）
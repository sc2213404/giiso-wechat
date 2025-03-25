# :robot: giiso_wechat：Windows 版智能体客户端

## 部署步骤 :gear:

### 1. **克隆代码** :octocat:

 ```bash
 git clone git@github.com:lyb-dev/giiso-projects.git
 ```

### 2. 安装所给版本微信 :iphone:

### 3. 配置环境 :wrench:

```bash

# 升级 pip
python -m pip install -U pip
# 安装必要依赖
pip install -r requirements.txt
# ChatGLM 还需要安装一个 kernel
ipython kernel install --name chatglm3 --user
# 安装对应版本ntwork
pip install ntwork-whl/ntwork-0.1.3-cp38-cp38-win_amd64.whl
```

### 4. 运行 :rocket:

```bash
python main.py
```
### 5. 响应被 @ 消息 :bell: 为了响应群聊消息，需要在 config.yaml 添加相应的 roomId。



#pragma once

#include <SDL3/SDL.h>

/// <summary>
/// C# 瘦宿主：创建 CoreCLR、加载 JoyGame.dll、反射调用 JoyGame.JoyEntry 的
/// OnInit / OnFrame / OnShutdown，并把 SDL 事件写进 cs 模块的输入桥。
/// 窗口与 r2d 渲染器由 C# 侧的 GameApp 自建。
/// </summary>
bool clr_host_init(int argc, char* argv[]);
SDL_AppResult clr_host_event(SDL_Event* e);
SDL_AppResult clr_host_iterate();
void clr_host_quit();
bool clr_host_quit_requested();
int clr_host_exit_code();

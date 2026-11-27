# ============================================================
# project_proxy2d —— 以 joy 的 examples/csharp（example_csharp）为模版的 2D 游戏工程
#
# native 侧只有瘦宿主（main.cpp / clr_host.cpp）：窗口、r2d 渲染、玩法与场景
# 全部在 CSharp/JoyGame.csproj 产出的 JoyGame.dll 里。
# 引擎以 submodule 形式位于 third_party/joy（内含 joy/ SDL/ msgpack/ spine/）。
# ============================================================
cmake_minimum_required(VERSION 3.16)
project(project_proxy2d C CXX)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/$<CONFIGURATION>")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/$<CONFIGURATION>")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/$<CONFIGURATION>")
set(CMAKE_INSTALL_PREFIX "${CMAKE_BINARY_DIR}" CACHE INTERNAL "")

if(MSVC)
    if(NOT CMAKE_GENERATOR STREQUAL "Ninja")
        add_definitions(/MP)
    endif()
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

set(JOY_REPO_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/joy")
if(NOT EXISTS "${JOY_REPO_DIR}/joy_add.cmake")
    message(FATAL_ERROR
        "未找到 ${JOY_REPO_DIR}/joy_add.cmake，请先执行：\n"
        "  git submodule update --init --recursive")
endif()

set(SDL_SHARED ON)
add_subdirectory("${JOY_REPO_DIR}/msgpack" "${CMAKE_BINARY_DIR}/msgpack")
add_subdirectory("${JOY_REPO_DIR}/spine"   "${CMAKE_BINARY_DIR}/spine")
add_subdirectory("${JOY_REPO_DIR}/SDL"     "${CMAKE_BINARY_DIR}/SDL")

# ---------- 启用 joy 的 C# 脚本模块（与 examples/csharp_host 同构） ----------
# 必须在 include(joy_add.cmake) 之前完成 CLR 探测并设置全局属性：
# joy_add_sources() 内部 include JoyTargets，模块在那一步读 JOY_REQUESTED_MODULES
# 决定编真胶水还是空桩。本项目不走 joy 主 CMake，故在这里独立完成探测。
set(JOY_CLR_ROOT "${JOY_REPO_DIR}/runtimes")
if(NOT MONO_INCLUDE_DIR)
    if(EXISTS "${JOY_CLR_ROOT}/include/mono-2.0")
        set(MONO_INCLUDE_DIR "${JOY_CLR_ROOT}/include/mono-2.0")
    elseif(WIN32 AND EXISTS "${JOY_CLR_ROOT}/windows-x64/include/mono-2.0")
        set(MONO_INCLUDE_DIR "${JOY_CLR_ROOT}/windows-x64/include/mono-2.0")
    endif()
endif()

# 桌面宿主经 hostfxr 动态加载 CoreCLR（jcsx.c），优先用系统安装的 dotnet；
# 运行时与 BCL 由 cmake/JoySelfContained.cmake 自包含部署到 exe 目录。
if(WIN32)
    if(NOT JOY_HOSTFXR_DLL)
        file(GLOB _hostfxr_candidates
            "C:/Program Files/dotnet/host/fxr/*/hostfxr.dll"
            "$ENV{DOTNET_ROOT}/host/fxr/*/hostfxr.dll")
        if(_hostfxr_candidates)
            list(GET _hostfxr_candidates -1 JOY_HOSTFXR_DLL)
        endif()
    endif()
    # dotnet root = hostfxr.dll 所在目录往上三级（<root>/host/fxr/<ver>/hostfxr.dll）。
    if(JOY_HOSTFXR_DLL)
        get_filename_component(_fxr_dir "${JOY_HOSTFXR_DLL}" DIRECTORY)
        get_filename_component(_fxr_host "${_fxr_dir}" DIRECTORY)
        get_filename_component(_fxr_host2 "${_fxr_host}" DIRECTORY)
        get_filename_component(JOY_DOTNET_ROOT "${_fxr_host2}" DIRECTORY)
    endif()
elseif(APPLE)
    if(NOT JOY_HOSTFXR_DLL)
        file(GLOB _hostfxr_candidates
            "/usr/local/share/dotnet/host/fxr/*/libhostfxr.dylib"
            "/usr/share/dotnet/host/fxr/*/libhostfxr.dylib"
            "$ENV{DOTNET_ROOT}/host/fxr/*/libhostfxr.dylib")
        if(_hostfxr_candidates)
            list(GET _hostfxr_candidates -1 JOY_HOSTFXR_DLL)
        endif()
    endif()
else()
    if(NOT JOY_HOSTFXR_DLL)
        file(GLOB _hostfxr_candidates
            "/usr/share/dotnet/host/fxr/*/libhostfxr.so"
            "/usr/lib/dotnet/host/fxr/*/libhostfxr.so"
            "$ENV{DOTNET_ROOT}/host/fxr/*/libhostfxr.so")
        if(_hostfxr_candidates)
            list(GET _hostfxr_candidates -1 JOY_HOSTFXR_DLL)
        endif()
    endif()
endif()

if(MONO_INCLUDE_DIR AND EXISTS "${MONO_INCLUDE_DIR}")
    set(JOY_MODULE_CS ON CACHE BOOL "C# 脚本模块" FORCE)
    set_property(GLOBAL PROPERTY JOY_REQUESTED_MODULES cs)
    message(STATUS "project_proxy2d: 启用 joy C# 模块")
    if(JOY_HOSTFXR_DLL)
        message(STATUS "project_proxy2d: hostfxr = ${JOY_HOSTFXR_DLL}")
    else()
        message(WARNING "project_proxy2d: 未找到 hostfxr，桌面 CoreCLR 宿主将无法启动")
    endif()
else()
    message(WARNING
        "project_proxy2d: 未找到 CLR 开发包（${JOY_CLR_ROOT}/include/mono-2.0），"
        "C# 模块跳过（只编空桩）。请确认 joy 子模块已完整 checkout。")
endif()

# ---------- native 瘦宿主 ----------
set(EXECUTABLE_NAME "project_proxy2d")
add_executable(${EXECUTABLE_NAME})

file(GLOB SRC_FILES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/*.h"
    "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp")
target_sources(${EXECUTABLE_NAME} PRIVATE ${SRC_FILES})

set_target_properties(${EXECUTABLE_NAME} PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)
if(MSVC)
    target_compile_options(${EXECUTABLE_NAME} PRIVATE /utf-8)
endif()

# 引入 joy 框架源码（纯文件注入，joy 的 .c 与本项目源码同 target 编译）
include("${JOY_REPO_DIR}/joy_add.cmake")
joy_add_sources(${EXECUTABLE_NAME})

# 项目根目录（clr_host.cpp 里 third_party/joy/... 的相对包含）
target_include_directories(${EXECUTABLE_NAME} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")

# CoreCLR 桌面宿主：把系统 dotnet root / hostfxr 路径传给 jcsx.c。
# 初始化前要设 DOTNET_ROOT，否则 hostfxr 从部署目录找不到 framework。
if(JOY_MODULE_CS)
    if(JOY_DOTNET_ROOT)
        target_compile_definitions(${EXECUTABLE_NAME} PRIVATE
            "JOY_DOTNET_ROOT=\"${JOY_DOTNET_ROOT}\"")
    endif()
    if(JOY_HOSTFXR_DLL)
        string(REPLACE "\\" "/" _hostfxr_cmake "${JOY_HOSTFXR_DLL}")
        target_compile_definitions(${EXECUTABLE_NAME} PRIVATE
            "JOY_HOSTFXR_PATH_MACRO=\"${_hostfxr_cmake}\"")
    endif()
    if(APPLE)
        set_target_properties(${EXECUTABLE_NAME} PROPERTIES
            BUILD_RPATH "@loader_path"
            INSTALL_RPATH "@loader_path")
    elseif(UNIX)
        set_target_properties(${EXECUTABLE_NAME} PROPERTIES
            BUILD_RPATH "$ORIGIN"
            INSTALL_RPATH "$ORIGIN")
    endif()
endif()

# ---------- 运行期资源：与 exe 同目录 ----------
set(_runtime_dir "${CMAKE_BINARY_DIR}/$<CONFIGURATION>")
add_custom_command(TARGET ${EXECUTABLE_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${CMAKE_CURRENT_SOURCE_DIR}/assets" "${_runtime_dir}"
    COMMENT "Copying assets next to ${EXECUTABLE_NAME}")

# ---------- C# 程序集：dotnet build 产出 JoyGame.dll + Joy.Bindings.dll ----------
if(JOY_MODULE_CS AND TARGET joy_module_cs)
    # IDE 里按 joy 真实目录树分组注入的引擎源码（source_group 只在当前目录生效）
    joy_ide_source_groups()

    set(_cs_proj "${CMAKE_CURRENT_SOURCE_DIR}/CSharp/JoyGame.csproj")
    set(_cs_out  "${CMAKE_BINARY_DIR}/CSharp")

    # 干净 checkout 没有 obj/：命令行 MSBuild 不隐式 restore，显式还原并串进依赖链。
    add_custom_target(project_proxy2d_cs_restore
        COMMAND dotnet restore "${_cs_proj}"
        COMMENT "dotnet restore CSharp (+ Joy.Bindings)"
        VERBATIM)
    add_custom_target(project_proxy2d_cs_managed
        COMMAND dotnet build "${_cs_proj}" -c $<IF:$<CONFIG:Debug>,Debug,Release> -o "${_cs_out}"
        BYPRODUCTS
            "${_cs_out}/JoyGame.dll"
            "${_cs_out}/Joy.Bindings.dll"
        COMMENT "dotnet build CSharp -> JoyGame.dll"
        VERBATIM)
    add_dependencies(project_proxy2d_cs_managed project_proxy2d_cs_restore)

    # ---- 桌面自包含运行时（与 joy example_csharp 同一套部署方式）----
    include("${JOY_REPO_DIR}/cmake/JoySelfContained.cmake")
    joy_deploy_selfcontained(${EXECUTABLE_NAME} "${_cs_proj}" "${_cs_out}"
                             "${_runtime_dir}" "$<IF:$<CONFIG:Debug>,Debug,Release>")
    # publish 也会编译 Joy.Bindings / JoyGame，必须排在 restore + dotnet build 之后，
    # 否则与 managed 并行时会抢写同一 csproj 的 obj/（NETSDK1004 / CS2012）。
    add_dependencies(${EXECUTABLE_NAME}_sc_publish project_proxy2d_cs_managed)
    add_dependencies(${EXECUTABLE_NAME}_sc_deploy project_proxy2d_cs_managed)

    add_custom_target(project_proxy2d_cs_deploy)
    add_dependencies(project_proxy2d_cs_deploy ${EXECUTABLE_NAME}_sc_deploy)
    add_dependencies(${EXECUTABLE_NAME} project_proxy2d_cs_deploy)

    # 自包含 runtimeconfig.json（无 framework 节点）与 exe 同目录。
    add_custom_command(TARGET ${EXECUTABLE_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_CURRENT_SOURCE_DIR}/CSharp/JoyGame.runtimeconfig.json"
                "${_runtime_dir}/JoyGame.runtimeconfig.json"
        COMMENT "Deploying self-contained JoyGame.runtimeconfig.json")

    # VS 解决方案挂入两个 C# 工程（否则 IDE 里看不到 .cs，且 NuGet restore
    # 缺引用项目信息会报 NU1105）。三个构建点串成链，避免 VS 与 dotnet build
    # 同时写同一 csproj 的 obj/。
    if(CMAKE_GENERATOR MATCHES "Visual Studio")
        include_external_msproject(JoyBindings "${JOY_BINDINGS_CSPROJ}" PLATFORM "Any CPU")
        include_external_msproject(JoyGame "${_cs_proj}" PLATFORM "Any CPU")
        add_dependencies(JoyBindings project_proxy2d_cs_restore)
        add_dependencies(JoyGame JoyBindings)
        add_dependencies(project_proxy2d_cs_managed JoyGame)
    endif()
endif()

# ---------- VS 调试：混合(.NET Core) 模式才能绑定 JoyGame.dll 断点 ----------
if(MSVC)
    set_target_properties(${EXECUTABLE_NAME} PROPERTIES
        VS_DEBUGGER_WORKING_DIRECTORY "${_runtime_dir}"
        VS_DEBUGGER_ENVIRONMENT "DOTNET_EnableDiagnostics=1\nCOMPlus_EnableDiagnostics=1"
        VS_USER_PROPS "${CMAKE_CURRENT_SOURCE_DIR}/cmake/Debugger.props")
    if(CMAKE_GENERATOR MATCHES "Visual Studio")
        configure_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/cmake/project_proxy2d.vcxproj.user.in"
            "${CMAKE_BINARY_DIR}/project_proxy2d.vcxproj.user" @ONLY)
    endif()
endif()
set_property(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" PROPERTY VS_STARTUP_PROJECT "${EXECUTABLE_NAME}")

# ---------- 冒烟测试：无窗口跑 180 帧，验证 C# 侧的模拟按键流程 ----------
enable_testing()
add_test(NAME project_proxy2d_smoke COMMAND ${EXECUTABLE_NAME} --smoke 180)
set_tests_properties(project_proxy2d_smoke PROPERTIES
    WORKING_DIRECTORY "${_runtime_dir}"
    ENVIRONMENT "SDL_VIDEODRIVER=dummy")

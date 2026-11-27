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

if((APPLE AND NOT CMAKE_SYSTEM_NAME MATCHES "Darwin") OR EMSCRIPTEN)
    set(BUILD_SHARED_LIBS OFF CACHE INTERNAL "")
    set(SDL_SHARED OFF)
else()
    set(SDL_SHARED ON)
endif()

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

add_subdirectory("${JOY_REPO_DIR}/msgpack" "${CMAKE_BINARY_DIR}/msgpack")
add_subdirectory("${JOY_REPO_DIR}/spine"   "${CMAKE_BINARY_DIR}/spine")
add_subdirectory("${JOY_REPO_DIR}/SDL"     "${CMAKE_BINARY_DIR}/SDL")

# ---------- 启用 joy 的 C# 脚本模块（与 examples/csharp_host 同构） ----------
# 必须在 include(joy_add.cmake) 之前完成 CLR 探测并设置全局属性：
# joy_add_sources() 内部 include JoyTargets，模块在那一步读 JOY_REQUESTED_MODULES
# 决定编真胶水还是空桩。本项目不走 joy 主 CMake，故在这里独立完成探测。
if(NOT EMSCRIPTEN)
    set(JOY_CLR_ROOT "${JOY_REPO_DIR}/runtimes")
    if(NOT JOY_CLR_PLATFORM)
        if(WIN32)
            set(JOY_CLR_PLATFORM "windows-x64")
        elseif(ANDROID)
            if(ANDROID_ABI STREQUAL "arm64-v8a")
                set(JOY_CLR_PLATFORM "android-arm64")
            elseif(ANDROID_ABI STREQUAL "armeabi-v7a")
                set(JOY_CLR_PLATFORM "android-armv7")
            elseif(ANDROID_ABI STREQUAL "x86_64")
                set(JOY_CLR_PLATFORM "android-x64")
            else()
                set(JOY_CLR_PLATFORM "android-${ANDROID_ABI}")
            endif()
        elseif(APPLE)
            set(JOY_CLR_PLATFORM "macos-arm64")
        else()
            set(JOY_CLR_PLATFORM "linux-x64")
        endif()
    endif()
    set(_clr_plat "${JOY_CLR_ROOT}/${JOY_CLR_PLATFORM}")

    if(NOT MONO_INCLUDE_DIR)
        if(EXISTS "${JOY_CLR_ROOT}/include/mono-2.0")
            set(MONO_INCLUDE_DIR "${JOY_CLR_ROOT}/include/mono-2.0")
        elseif(EXISTS "${_clr_plat}/include/mono-2.0")
            set(MONO_INCLUDE_DIR "${_clr_plat}/include/mono-2.0")
        endif()
    endif()

    if(NOT MONO_LIBRARIES)
        if(WIN32 AND EXISTS "${_clr_plat}/coreclr.import.lib")
            set(MONO_LIBRARIES "${_clr_plat}/coreclr.import.lib")
        elseif(EXISTS "${_clr_plat}/libmonosgen-2.0.so")
            # Android 的 MonoVM 原生库叫 libmonosgen-2.0.so，不是 libcoreclr.so。
            set(MONO_LIBRARIES "${_clr_plat}/libmonosgen-2.0.so")
        elseif(EXISTS "${_clr_plat}/libcoreclr.so")
            set(MONO_LIBRARIES "${_clr_plat}/libcoreclr.so")
        elseif(EXISTS "${_clr_plat}/libcoreclr.dylib")
            set(MONO_LIBRARIES "${_clr_plat}/libcoreclr.dylib")
        elseif(EXISTS "${_clr_plat}/libmonosgen-2.0.dylib")
            set(MONO_LIBRARIES "${_clr_plat}/libmonosgen-2.0.dylib")
        endif()
    endif()

    # Android：MonoVM 运行时从 runtimes/nupkg 解包暂存，与桌面用同一套来源。
    if(ANDROID)
        include("${JOY_REPO_DIR}/cmake/JoyMonoVm.cmake")
        joy_monovm_stage(_joy_monovm_stage)
        set(MONO_LIBRARIES "${_joy_monovm_stage}/libmonosgen-2.0.so")
    endif()

    # CoreCLR 桌面宿主经 hostfxr 动态加载（Android 走 libmonosgen 的 coreclr_*，不需要）。
    if(WIN32 AND NOT ANDROID)
        if(NOT JOY_HOSTFXR_DLL)
            file(GLOB _hostfxr_candidates
                "C:/Program Files/dotnet/host/fxr/*/hostfxr.dll"
                "$ENV{DOTNET_ROOT}/host/fxr/*/hostfxr.dll"
                "${_clr_plat}/hostfxr.dll")
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
    elseif(UNIX AND NOT ANDROID)
        if(NOT JOY_HOSTFXR_DLL)
            file(GLOB _hostfxr_candidates
                "/usr/share/dotnet/host/fxr/*/libhostfxr.so"
                "/usr/lib/dotnet/host/fxr/*/libhostfxr.so"
                "$ENV{DOTNET_ROOT}/host/fxr/*/libhostfxr.so"
                "${_clr_plat}/libhostfxr.so")
            if(_hostfxr_candidates)
                list(GET _hostfxr_candidates -1 JOY_HOSTFXR_DLL)
            endif()
        endif()
    endif()

    # 桌面不再要求 MONO_LIBRARIES 哨兵：jcsx.c 动态加载 hostfxr，运行时与 BCL
    # 由 cmake/JoySelfContained.cmake 自包含部署。Android 必须有 libmonosgen 主库。
    if(MONO_INCLUDE_DIR AND EXISTS "${MONO_INCLUDE_DIR}" AND (NOT ANDROID OR MONO_LIBRARIES))
        set(JOY_MODULE_CS ON CACHE BOOL "C# 脚本模块" FORCE)
        set_property(GLOBAL PROPERTY JOY_REQUESTED_MODULES cs)
        message(STATUS "project_proxy2d: 启用 joy C# 模块 (${JOY_CLR_PLATFORM})")
        if(NOT ANDROID)
            if(JOY_HOSTFXR_DLL)
                message(STATUS "project_proxy2d: hostfxr = ${JOY_HOSTFXR_DLL}")
            else()
                message(WARNING "project_proxy2d: 未找到 hostfxr，桌面 CoreCLR 宿主将无法启动")
            endif()
        endif()
    else()
        message(WARNING
            "project_proxy2d: 未找到 CLR 开发包（${JOY_CLR_ROOT}/include/mono-2.0），"
            "C# 模块跳过（只编空桩）。请确认 joy 子模块已完整 checkout。")
    endif()
endif()

# ---------- native 瘦宿主 ----------
# Android 的 APK 入口库必须叫 main；桌面用项目名。
if(ANDROID)
    set(MOBILE_ASSETS_DIR "${MOBILE_MAIN_DIR}/assets")
    message(STATUS "MOBILE_ASSETS_DIR = '${MOBILE_ASSETS_DIR}'")
    set(EXECUTABLE_NAME "main")
    add_library(${EXECUTABLE_NAME} SHARED)
else()
    set(EXECUTABLE_NAME "project_proxy2d")
    add_executable(${EXECUTABLE_NAME})
endif()

file(GLOB SRC_FILES CONFIGURE_DEPENDS "*.h" "*.c" "*.hpp" "*.cpp")
target_sources(${EXECUTABLE_NAME} PRIVATE
    ${SRC_FILES}
    iosLaunchScreen.storyboard)

# Windows 平台嵌入 .exe 图标
if(WIN32)
    target_sources(${EXECUTABLE_NAME} PRIVATE app_icon.rc)
endif()

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
if(JOY_MODULE_CS AND NOT ANDROID)
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

# ---------- 运行期资源：桌面拷到 exe 旁，Android 拷到 APK assets ----------
set(ASSETS_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/assets")
file(GLOB_RECURSE ALL_ASSET_FILES "${ASSETS_ROOT}/*")
set(ASSET_FILES "")
foreach(_file ${ALL_ASSET_FILES})
    if(NOT _file MATCHES "\\.svn/" AND NOT _file MATCHES "/\\.git/")
        file(RELATIVE_PATH _rel "${ASSETS_ROOT}" "${_file}")
        list(APPEND ASSET_FILES "${_rel}")
    endif()
endforeach()

if(APPLE AND NOT ANDROID)
    foreach(_asset ${ASSET_FILES})
        get_filename_component(_dir "${_asset}" DIRECTORY)
        target_sources(${EXECUTABLE_NAME} PRIVATE "${ASSETS_ROOT}/${_asset}")
        set_property(SOURCE "${ASSETS_ROOT}/${_asset}" PROPERTY
            MACOSX_PACKAGE_LOCATION "Resources/${_dir}")
    endforeach()
else()
    if(UNIX AND NOT APPLE AND NOT ANDROID)
        target_link_libraries(${EXECUTABLE_NAME} PRIVATE m)
    endif()
    foreach(_asset ${ASSET_FILES})
        get_filename_component(_rel_dir "${_asset}" DIRECTORY)
        if(ANDROID)
            set(_asset_outdir "${MOBILE_ASSETS_DIR}/${_rel_dir}")
            set(_asset_outfile "${MOBILE_ASSETS_DIR}/${_asset}")
        else()
            set(_asset_outdir "${CMAKE_BINARY_DIR}/$<CONFIGURATION>/${_rel_dir}")
            set(_asset_outfile "${CMAKE_BINARY_DIR}/$<CONFIGURATION>/${_asset}")
        endif()
        add_custom_command(TARGET ${EXECUTABLE_NAME} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E make_directory "${_asset_outdir}"
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${ASSETS_ROOT}/${_asset}" "${_asset_outfile}")
    endforeach()
endif()

# ---------- 平台特定属性 ----------
set(RESOURCE_FILES "")
if(IOS)
    set(RESOURCE_FILES "iosLaunchScreen.storyboard")
endif()
set_target_properties(${EXECUTABLE_NAME} PROPERTIES
    MACOSX_BUNDLE TRUE
    MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/Info.plist.in"
    XCODE_GENERATE_SCHEME TRUE
    XCODE_ATTRIBUTE_BUNDLE_IDENTIFIER "com.game.${PROJECT_NAME}"
    XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "com.game.${PROJECT_NAME}"
    XCODE_ATTRIBUTE_CURRENTYEAR "${CURRENTYEAR}"
    RESOURCE "${RESOURCE_FILES}"
)

# ---------- C# 程序集：dotnet build 产出 JoyGame.dll + Joy.Bindings.dll ----------
if(JOY_MODULE_CS AND TARGET joy_module_cs AND NOT EMSCRIPTEN)
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

    if(ANDROID)
        # Android：程序集进 APK assets 根，BCL/绑定进 assets/lib（见 clr_host.cpp）。
        set(_cs_runtime_dir "${MOBILE_ASSETS_DIR}")
        add_custom_target(project_proxy2d_cs_deploy
            COMMAND ${CMAKE_COMMAND} -E make_directory "${_cs_runtime_dir}"
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${_cs_out}/JoyGame.dll" "${_cs_runtime_dir}/JoyGame.dll"
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${_cs_out}/JoyGame.pdb" "${_cs_runtime_dir}/JoyGame.pdb"
            DEPENDS project_proxy2d_cs_managed
            COMMENT "Syncing JoyGame.dll/pdb to Android assets")
        add_dependencies(${EXECUTABLE_NAME} project_proxy2d_cs_deploy)

        get_filename_component(_clr_bin "${MONO_LIBRARIES}" DIRECTORY)
        file(GLOB _clr_lib_files LIST_DIRECTORIES false "${_clr_bin}/libs/*")
        set(_copy_lib_cmds)
        foreach(_lib IN LISTS _clr_lib_files)
            list(APPEND _copy_lib_cmds
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                        "${_lib}" "${_cs_runtime_dir}/lib/")
        endforeach()
        add_custom_command(TARGET ${EXECUTABLE_NAME} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E make_directory "${_cs_runtime_dir}/lib"
            ${_copy_lib_cmds}
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${_cs_out}/Joy.Bindings.dll" "${_cs_runtime_dir}/lib/Joy.Bindings.dll"
            COMMENT "Deploying Android BCL + Joy.Bindings.dll")

        # MonoVM 主库 + libSystem.* shim 必须进 APK 的 lib/<abi>（assets 里的 .so 不可 dlopen）。
        file(GLOB _clr_shims "${_clr_bin}/libSystem.*.so")
        set(_clr_so_files "${MONO_LIBRARIES}" ${_clr_shims})
        set(_apk_libs "${CMAKE_BINARY_DIR}/lib/${ANDROID_ABI}")
        if(MOBILE_MAIN_DIR)
            get_filename_component(_gradle_app_dir "${MOBILE_MAIN_DIR}/.." ABSOLUTE)
            list(APPEND _apk_libs "${_gradle_app_dir}/libs/${ANDROID_ABI}")
        endif()
        foreach(_apk_lib IN LISTS _apk_libs)
            add_custom_command(TARGET ${EXECUTABLE_NAME} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E make_directory "${_apk_lib}"
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                        ${_clr_so_files} "${_apk_lib}/"
                COMMENT "Deploying MonoVM + CoreLib shims into ${_apk_lib}")
        endforeach()
    else()
        # ---- 桌面自包含运行时（与 joy example_csharp 同一套部署方式）----
        set(_runtime_dir "${CMAKE_BINARY_DIR}/$<CONFIGURATION>")
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

        # Joy.Bindings 必须与 JoyGame 同目录（同一 AssemblyLoadContext 解析依赖）。
        add_custom_command(TARGET ${EXECUTABLE_NAME} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${_cs_out}/Joy.Bindings.dll" "${_runtime_dir}/Joy.Bindings.dll"
            COMMENT "Deploying Joy.Bindings.dll")
        # 自包含 runtimeconfig.json（无 framework 节点）与 exe 同目录。
        add_custom_command(TARGET ${EXECUTABLE_NAME} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${CMAKE_CURRENT_SOURCE_DIR}/CSharp/JoyGame.runtimeconfig.json"
                    "${_runtime_dir}/JoyGame.runtimeconfig.json"
            COMMENT "Deploying self-contained JoyGame.runtimeconfig.json")
    endif()

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
        VS_DEBUGGER_WORKING_DIRECTORY "${CMAKE_BINARY_DIR}/$<CONFIGURATION>"
        VS_DEBUGGER_ENVIRONMENT "DOTNET_EnableDiagnostics=1\nCOMPlus_EnableDiagnostics=1"
        VS_USER_PROPS "${CMAKE_CURRENT_SOURCE_DIR}/cmake/Debugger.props")
    if(CMAKE_GENERATOR MATCHES "Visual Studio")
        configure_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/cmake/project_proxy2d.vcxproj.user.in"
            "${CMAKE_BINARY_DIR}/project_proxy2d.vcxproj.user" @ONLY)
    endif()
endif()
set_property(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" PROPERTY VS_STARTUP_PROJECT "${EXECUTABLE_NAME}")

# ---------- macOS 打包（非 Xcode 生成器） ----------
if(CMAKE_SYSTEM_NAME MATCHES "Darwin" AND NOT CMAKE_GENERATOR MATCHES "Xcode")
    install(TARGETS ${EXECUTABLE_NAME}
        BUNDLE DESTINATION ./install COMPONENT Runtime
        RUNTIME DESTINATION ./install/bin COMPONENT Runtime)
    set(DEP_DIR "${CMAKE_BINARY_DIR}")
    install(CODE "
        include(BundleUtilities)
        fixup_bundle(\"\$<TARGET_BUNDLE_DIR:${EXECUTABLE_NAME}>\" \"\" \"${DEP_DIR}\")
    ")
    set(CPACK_GENERATOR "DragNDrop")
    include(CPack)
endif()

# ---------- 冒烟测试：无窗口跑 180 帧，验证 C# 侧的模拟按键流程 ----------
if(NOT ANDROID)
    enable_testing()
    add_test(NAME project_proxy2d_smoke COMMAND ${EXECUTABLE_NAME} --smoke 180)
    set_tests_properties(project_proxy2d_smoke PROPERTIES
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}/$<CONFIGURATION>"
        ENVIRONMENT "SDL_VIDEODRIVER=dummy")
endif()

source_group(TREE "${CMAKE_CURRENT_SOURCE_DIR}/.." FILES ${SRC_FILES})

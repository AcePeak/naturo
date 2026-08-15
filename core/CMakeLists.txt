cmake_minimum_required(VERSION 3.16)
# C is enabled alongside C++ so the vendored MinHook C sources (third_party/
# minhook/src/*.c) compile with the C compiler instead of being treated as
# non-build "None" items by the Visual Studio generator.
project(naturo_core VERSION 0.3.3 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Shared library
add_library(naturo_core SHARED
    src/version.cpp
    src/capture.cpp
    src/window.cpp
    src/element.cpp
    src/input.cpp
    src/msaa.cpp
    src/ia2.cpp
    src/jab.cpp
    # Win32 API hooking (MinHook). The C ABI + manager compile everywhere
    # (Windows-only internals are guarded); the MinHook C sources and detours
    # are Windows/x86-x64 only and added below.
    src/hooks/minhook_wrapper.cpp
    src/hooks/hook_manager.cpp
)

target_include_directories(naturo_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# ── MinHook (vendored, MIT) ───────────────────────────────────────────
# MinHook is a small C trampoline-hooking library. Compile its sources
# directly into naturo_core on Windows (it targets x86/x64 Windows only).
if(WIN32)
    set(MINHOOK_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/minhook)
    target_sources(naturo_core PRIVATE
        ${MINHOOK_DIR}/src/buffer.c
        ${MINHOOK_DIR}/src/hook.c
        ${MINHOOK_DIR}/src/trampoline.c
        ${MINHOOK_DIR}/src/hde/hde32.c
        ${MINHOOK_DIR}/src/hde/hde64.c
    )
    target_include_directories(naturo_core PRIVATE ${MINHOOK_DIR}/include)
    target_include_directories(naturo_core PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/hooks)
endif()

target_compile_definitions(naturo_core PRIVATE NATURO_BUILDING)

# Windows-specific link libraries
if(WIN32)
    target_link_libraries(naturo_core PRIVATE
        gdi32
        user32
        ole32
        oleaut32
        psapi
        advapi32
        imm32
    )
endif()

# On Windows, put DLL in bin/
set_target_properties(naturo_core PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
)

# Tests
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()

    # Version / lifecycle tests
    add_executable(test_naturo_core tests/test_version.cpp)
    target_link_libraries(test_naturo_core PRIVATE naturo_core)
    set_target_properties(test_naturo_core PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    )
    add_test(NAME test_version COMMAND test_naturo_core)

    # Capture tests (Windows only — uses GDI)
    if(WIN32)
        add_executable(test_capture tests/test_capture.cpp)
        target_link_libraries(test_capture PRIVATE naturo_core)
        set_target_properties(test_capture PROPERTIES
            RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        )
        add_test(NAME test_capture COMMAND test_capture)

        # Window listing tests
        add_executable(test_window tests/test_window.cpp)
        target_link_libraries(test_window PRIVATE naturo_core)
        set_target_properties(test_window PROPERTIES
            RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        )
        add_test(NAME test_window COMMAND test_window)

        # UI element tree tests
        add_executable(test_element tests/test_element.cpp)
        target_link_libraries(test_element PRIVATE naturo_core)
        set_target_properties(test_element PROPERTIES
            RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        )
        add_test(NAME test_element COMMAND test_element)

        # Phase 2 input tests
        add_executable(test_input tests/test_input.cpp)
        target_link_libraries(test_input PRIVATE naturo_core)
        set_target_properties(test_input PROPERTIES
            RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        )
        add_test(NAME test_input COMMAND test_input)
    endif()
endif()

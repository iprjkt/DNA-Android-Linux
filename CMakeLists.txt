cmake_minimum_required(VERSION 3.20)
project(dna_backend VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Optimization flags
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-O3 -Wall -Wextra -Wno-unused-parameter)
endif()

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/cpp/include
)

# Core library sources
set(DNA_CORE_SOURCES
    cpp/src/detection.cpp
    cpp/src/prop.cpp
    cpp/src/sparse.cpp
    cpp/src/fs_metadata.cpp
    cpp/src/patch.cpp
    cpp/src/debloat.cpp
    cpp/src/rom_tweaks.cpp
)

# Static core library
add_library(dna_core_static STATIC ${DNA_CORE_SOURCES})
target_include_directories(dna_core_static PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/cpp/include)

# Pybind11 Python extension module
find_package(pybind11 CONFIG QUIET)
if(NOT pybind11_FOUND)
    execute_process(
        COMMAND python3 -m pybind11 --cmakedir
        OUTPUT_VARIABLE PYBIND11_CMAKEDIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE PYBIND11_RES
    )
    if(PYBIND11_RES EQUAL 0)
        list(APPEND CMAKE_PREFIX_PATH ${PYBIND11_CMAKEDIR})
        find_package(pybind11 REQUIRED CONFIG)
    else()
        message(FATAL_ERROR "pybind11 not found! Install it via pip or package manager.")
    endif()
endif()

pybind11_add_module(dna_core_cpp cpp/bindings/py_dna.cpp)
target_link_libraries(dna_core_cpp PRIVATE dna_core_static)

# Output python module directly into dna_core/ for instant import
set_target_properties(dna_core_cpp PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/dna_core
)

# Standalone native C++ CLI runner
add_executable(dna_native_cli cpp/src/main_cli.cpp)
target_link_libraries(dna_native_cli PRIVATE dna_core_static)

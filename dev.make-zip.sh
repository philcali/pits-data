#!/bin/bash

function clean() {
    rm -rf lambda_env
}

function clean_previous_builds() {
    local previous_build
    for previous_build in $(find . -maxdepth 1 -name "*.zip"); do
        echo "Removing $previous_build"
        rm -f $previous_build
    done
}

function setup_and_activate_venv() {
    python3 -m venv lambda_env
    source lambda_env/bin/activate
}

function prepare_deps_and_deactive() {
    pip install -r requirements.txt
    deactivate
}

function create_archive() {
    local python_version=$(python3 --version | sed -E 's|Python (\w+\.\w+)\.\w+$|\1|')
    local zip_name=$1
    cd lambda_env/lib/python${python_version}/site-packages
    zip -r ../../../../$zip_name .
    cd ../../../../
}

function add_current_code() {
    zip -r -g $1 pinthesky
}

function main() {
    local zip_name="build_function.zip"
    clean_previous_builds
    clean
    setup_and_activate_venv
    prepare_deps_and_deactive
    create_archive $zip_name
    add_current_code $zip_name
    clean
    echo "Created application ready for deployment:"
    echo $zip_name
}

main
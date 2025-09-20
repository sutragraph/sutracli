class SystemInfoParams {
  os string
  shell string
  home string
  current_dir string
}

template_string SystemInfo(params:SystemInfoParams) #"
## SYSTEM INFORMATION

os: {{ params.os }}
shell: {{ params.shell }}
home: {{ params.home }}
cwd: {{ params.current_dir }}
"#

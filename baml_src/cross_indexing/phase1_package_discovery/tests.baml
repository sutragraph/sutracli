test TestAwsPackageDiscovery {
  functions [AwsPackageDiscovery]
  args {
    analysis_query "Analyze the Python packages and dependencies in this project to understand the core functionality and technology stack"
    memory_context "Starting package discovery analysis for a Python CLI project"
    system_info {
      home "/home/user"
      current_dir "/home/user/project"  
    }
  }
}

test TestAwsPackageDiscoveryWithEmptyMemory {
  functions [AwsPackageDiscovery]
  args {
    analysis_query "Identify all Python packages and their usage patterns in the codebase"
    memory_context ""
    system_info {
      home "/home/testuser"
      current_dir "/home/testuser/testproject"
    }
  }
}

test TestAwsPackageDiscoveryComplexQuery {
  functions [AwsPackageDiscovery]
  args {
    analysis_query "Perform a comprehensive analysis of package dependencies, including external libraries, internal modules, and their interconnections to map the project architecture"
    memory_context "Previous analysis identified Flask and SQLAlchemy as primary dependencies. Need to explore deeper connections and usage patterns."
    system_info {
      home "/opt/projects"
      current_dir "/opt/projects/webapp"
    }
  }
}

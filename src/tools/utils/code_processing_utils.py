"""
Code processing utility functions for handling code snippets, chunking, and line processing.
"""


def merge_overlapping_ranges(ranges):
    """
    Merge overlapping line ranges for the same file.

    Args:
        ranges: List of tuples [(start_line, end_line), ...]

    Returns:
        List of merged non-overlapping ranges
    """
    if not ranges:
        return []

    # Sort ranges by start line
    sorted_ranges = sorted(ranges, key=lambda x: x[0])
    merged = []

    current_start, current_end = sorted_ranges[0]

    for start, end in sorted_ranges[1:]:
        # Check if current range overlaps with the next range
        if start <= current_end + 1:  # +1 allows for adjacent ranges to be merged
            # Merge by extending the current range
            current_end = max(current_end, end)
        else:
            # No overlap, add current range to result and start new range
            merged.append((current_start, current_end))
            current_start, current_end = start, end

    # Add the last range
    merged.append((current_start, current_end))

    return merged


def add_line_numbers_to_code(code_snippet, start_line=None):
    """
    Add line numbers to code snippet for better LLM understanding.

    Args:
        code_snippet: The code content
        start_line: Starting line number (1-based)

    Returns:
        Code with line numbers added
    """
    if not code_snippet:
        return code_snippet

    lines = code_snippet.split("\n")
    numbered_lines = []

    if start_line is not None:
        # Use provided start line
        for i, line in enumerate(lines):
            line_num = start_line + i
            numbered_lines.append(f"{line_num:4d} | {line}")
        return "\n".join(numbered_lines)
    else:
        # Default numbering from 1
        for i, line in enumerate(lines, 1):
            numbered_lines.append(f"{i:4d} | {line}")
        return "\n".join(numbered_lines)


def process_code_with_line_filtering(
    code_snippet, file_start_line=1, start_line=None, end_line=None
):
    """
    Process full code content and filter by line ranges if specified.

    Args:
        code_snippet: The full code content
        file_start_line: The starting line number of the code snippet in the file
        start_line: Optional start line for filtering (absolute line number)
        end_line: Optional end line for filtering (absolute line number)

    Returns:
        Dictionary with filtered code and metadata
    """
    if not code_snippet:
        return {
            "code": "",
            "filtered": False,
            "actual_start_line": file_start_line,
            "actual_end_line": file_start_line,
            "total_lines": 0,
        }

    lines = code_snippet.split("\n")
    total_lines = len(lines)

    # If no filtering requested, return full code with line numbers
    if start_line is None and end_line is None:
        numbered_code = add_line_numbers_to_code(code_snippet, file_start_line)
        return {
            "code": numbered_code,
            "filtered": False,
            "actual_start_line": file_start_line,
            "actual_end_line": file_start_line + total_lines - 1,
            "total_lines": total_lines,
        }

    # Calculate relative positions in the code array
    file_end_line = file_start_line + total_lines - 1

    # Determine actual filtering bounds
    actual_start_line = max(start_line or file_start_line, file_start_line)
    actual_end_line = min(end_line or file_end_line, file_end_line)

    # Convert to 0-based indices for array slicing
    start_idx = actual_start_line - file_start_line
    end_idx = actual_end_line - file_start_line + 1

    # Extract the filtered lines
    filtered_lines = lines[start_idx:end_idx]
    filtered_code = "\n".join(filtered_lines)

    # Add line numbers to the filtered code
    numbered_code = add_line_numbers_to_code(filtered_code, actual_start_line)

    return {
        "code": numbered_code,
        "filtered": True,
        "actual_start_line": actual_start_line,
        "actual_end_line": actual_end_line,
        "total_lines": len(filtered_lines),
    }


def chunk_large_code_clean(code_snippet, max_lines, chunk_threshold, file_start_line=1):
    """
    Split large code content into clean, non-overlapping chunks.
    Only chunks if total lines > chunk_threshold to avoid unnecessary chunking.

    Args:
        code_snippet: The code content
        file_start_line: Starting line number in the original file

    Returns:
        List of dictionaries with chunk information
    """
    from loguru import logger

    logger.debug(f"📦 Chunking file: max_lines={max_lines}, threshold={chunk_threshold}")
    if not code_snippet:
        logger.debug("❌ No code snippet provided")
        return [
            {
                "content": "",
                "chunk_num": 1,
                "total_chunks": 1,
                "start_line": file_start_line,
                "end_line": file_start_line,
                "total_lines": 0,
            }
        ]

    lines = code_snippet.split("\n")
    total_lines = len(lines)

    logger.debug(f"📦 Content has {total_lines} lines")

    if total_lines <= chunk_threshold:
        logger.debug(
            f"📊 File too small ({total_lines} <= {chunk_threshold}) - no chunking needed"
        )
        numbered_code = add_line_numbers_to_code(code_snippet, file_start_line)

        return [
            {
                "content": numbered_code,
                "chunk_num": 1,
                "total_chunks": 1,
                "start_line": file_start_line,
                "end_line": file_start_line + total_lines - 1,
                "total_lines": total_lines,
                "original_file_lines": total_lines,
            }
        ]

    logger.debug(f"📦 File requires chunking ({total_lines} > {chunk_threshold})")

    # Smart chunking: avoid small trailing chunks
    # Calculate optimal chunk distribution
    estimated_chunks = (total_lines + max_lines - 1) // max_lines  # Ceiling division
    remaining_after_full_chunks = total_lines % max_lines

    # If the last chunk would be very small (< 50 lines), redistribute
    if (
        estimated_chunks > 1
        and remaining_after_full_chunks > 0
        and remaining_after_full_chunks < 50
    ):
        logger.debug("📦 Using redistribution to avoid small trailing chunk")
        # Redistribute lines more evenly
        lines_per_chunk = total_lines // (estimated_chunks - 1)
        extra_lines = total_lines % (estimated_chunks - 1)

        chunks = []
        start_idx = 0

        for chunk_num in range(1, estimated_chunks):  # One less chunk
            # Distribute extra lines among first chunks
            chunk_size = lines_per_chunk + (1 if chunk_num <= extra_lines else 0)
            end_idx = min(start_idx + chunk_size, total_lines)

            chunk_lines = lines[start_idx:end_idx]
            chunk_content = "\n".join(chunk_lines)

            chunk_start_line = file_start_line + start_idx
            chunk_end_line = file_start_line + end_idx - 1

            numbered_chunk = add_line_numbers_to_code(chunk_content, chunk_start_line)

            chunks.append(
                {
                    "content": numbered_chunk,
                    "chunk_num": chunk_num,
                    "total_chunks": estimated_chunks - 1,
                    "start_line": chunk_start_line,
                    "end_line": chunk_end_line,
                    "total_lines": len(chunk_lines),
                    "original_file_lines": total_lines,
                }
            )

        start_idx = end_idx

    else:
        # Regular chunking for normal cases
        chunks = []
        chunk_num = 1
        start_idx = 0

        while start_idx < total_lines:
            end_idx = min(start_idx + max_lines, total_lines)
            chunk_lines = lines[start_idx:end_idx]
            chunk_content = "\n".join(chunk_lines)

            chunk_start_line = file_start_line + start_idx
            chunk_end_line = file_start_line + end_idx - 1

            numbered_chunk = add_line_numbers_to_code(chunk_content, chunk_start_line)

            chunks.append(
                {
                    "content": numbered_chunk,
                    "chunk_num": chunk_num,
                    "total_chunks": 0,  # Will be updated after all chunks are created
                    "start_line": chunk_start_line,
                    "end_line": chunk_end_line,
                    "total_lines": len(chunk_lines),
                    "original_file_lines": total_lines,
                }
            )

            start_idx = end_idx
            chunk_num += 1

    # Update total_chunks and original_file_lines for all chunks
    total_chunks = len(chunks)

    for chunk in chunks:
        chunk["total_chunks"] = total_chunks
        chunk["original_file_lines"] = total_lines

    logger.debug(f"📦 Chunking completed - created {len(chunks)} chunks")

    return chunks

"""
Code processing utility functions for handling code snippets, chunking, and line processing.
"""


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


def chunk_large_code_clean(code_snippet, file_start_line=1, max_lines=200, chunk_threshold=250):
    """
    Split large code content into clean, non-overlapping chunks.
    Only chunks if total lines > chunk_threshold to avoid unnecessary chunking.

    Args:
        code_snippet: The code content
        file_start_line: Starting line number in the original file
        max_lines: Maximum lines per chunk (default 200)
        chunk_threshold: Only chunk if total lines > this threshold (default 250)

    Returns:
        List of dictionaries with chunk information
    """
    if not code_snippet:
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

    # Only chunk if file is larger than threshold (e.g., >250 lines)
    # This prevents chunking 223 lines into 0-200, 201-223
    if total_lines <= chunk_threshold:
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

    # Smart chunking: avoid small trailing chunks
    # Calculate optimal chunk distribution
    estimated_chunks = (total_lines + max_lines - 1) // max_lines  # Ceiling division
    remaining_after_full_chunks = total_lines % max_lines

    # If the last chunk would be very small (< 50 lines), redistribute
    if estimated_chunks > 1 and remaining_after_full_chunks > 0 and remaining_after_full_chunks < 50:
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

    return chunks


def create_context_aware_chunks(
    code_snippet, start_line=None, target_range=None, max_lines=200, context_lines=50
):
    """
    Create chunks that are optimized for code changes spanning multiple chunks.

    Args:
        code_snippet: The code content
        start_line: Starting line number
        target_range: Tuple of (start_line, end_line) for the target change area
        max_lines: Maximum lines per chunk
        context_lines: Extra context lines around target range

    Returns:
        List of dictionaries with chunk information optimized for changes
    """
    if not code_snippet:
        return chunk_large_code_clean(code_snippet, start_line, max_lines)

    lines = code_snippet.split("\n")
    total_lines = len(lines)

    # If no target range specified or file is small, use regular chunking
    if not target_range or total_lines <= max_lines:
        return chunk_large_code_clean(code_snippet, start_line, max_lines)

    target_start, target_end = target_range
    file_start_line = start_line or 1

    # Convert absolute line numbers to relative positions in the code
    rel_target_start = max(0, target_start - file_start_line)
    rel_target_end = min(total_lines - 1, target_end - file_start_line)

    # If target range is within a single chunk, use regular chunking
    if rel_target_end - rel_target_start <= max_lines - (2 * context_lines):
        return chunk_large_code_clean(code_snippet, start_line, max_lines)

    # Create context-aware chunks
    chunks = []

    # Strategy: Create chunks that ensure the target range has good context
    chunk_start = max(0, rel_target_start - context_lines)
    chunk_num = 1

    while chunk_start < total_lines:
        chunk_end = min(chunk_start + max_lines, total_lines)

        # Ensure we don't cut off in the middle of the target range
        if (
            chunk_start <= rel_target_end
            and chunk_end > rel_target_start
            and chunk_end < rel_target_end
            and chunk_end < total_lines
        ):
            # Extend this chunk to include more of the target range
            chunk_end = min(rel_target_end + context_lines, total_lines)

        chunk_lines = lines[chunk_start:chunk_end]
        chunk_content = "\n".join(chunk_lines)

        chunk_start_line = file_start_line + chunk_start
        chunk_end_line = file_start_line + chunk_end - 1

        # Calculate which part of the target range is in this chunk
        target_in_chunk_start = max(target_start, chunk_start_line)
        target_in_chunk_end = min(target_end, chunk_end_line)
        has_target_content = (
            chunk_start_line <= target_end and chunk_end_line >= target_start
        )

        chunks.append(
            {
                "content": chunk_content,
                "chunk_num": chunk_num,
                "total_chunks": 0,  # Will be updated after all chunks are created
                "start_line": chunk_start_line,
                "end_line": chunk_end_line,
                "total_lines": total_lines,
                "has_target_content": has_target_content,
                "target_range_in_chunk": (
                    (target_in_chunk_start, target_in_chunk_end)
                    if has_target_content
                    else None
                ),
                "is_context_aware": True,
            }
        )

        # Move to next chunk
        if chunk_end >= total_lines:
            break

        # Smart positioning for next chunk
        if chunk_end <= rel_target_end:
            # Still within target range, continue with overlap
            chunk_start = chunk_end - context_lines
        else:
            # Past target range, use regular chunking
            chunk_start = chunk_end

        chunk_num += 1

    # Update total_chunks for all chunks
    total_chunks = len(chunks)
    for chunk in chunks:
        chunk["total_chunks"] = total_chunks

    return chunks

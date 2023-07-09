def chunks(content, chunk_size: int) -> list:
    chunks_ = []
    for idx in range(0, len(content), chunk_size):
        chunks_.append(content[idx : idx + chunk_size])
    return chunks_

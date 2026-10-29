"""用标准库验证 PNG 的完整结构、校验和及可解压像素数据；不判断画面内容。"""
import struct
import zlib


def validate_png(payload):
    if not payload.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('预览证据须保存为 PNG；不支持仅凭文件头确认 JPEG')
    position, image, compressed, palette, ended = 8, None, bytearray(), False, False
    while position < len(payload):
        if position + 12 > len(payload):
            raise ValueError('PNG 文件截断')
        length = struct.unpack('>I', payload[position:position + 4])[0]
        kind = payload[position + 4:position + 8]
        stop = position + 12 + length
        if stop > len(payload):
            raise ValueError('PNG 数据块截断')
        body = payload[position + 8:position + 8 + length]
        checksum = struct.unpack('>I', payload[position + 8 + length:stop])[0]
        if zlib.crc32(kind + body) & 0xffffffff != checksum:
            raise ValueError('PNG 数据块校验和错误')
        if image is None and kind != b'IHDR':
            raise ValueError('PNG 缺少首部')
        if kind == b'IHDR':
            if image is not None or length != 13:
                raise ValueError('PNG 首部无效')
            image = struct.unpack('>IIBBBBB', body)
        elif kind == b'PLTE':
            if not length or length % 3 or length > 768:
                raise ValueError('PNG 调色板无效')
            palette = True
        elif kind == b'IDAT':
            compressed.extend(body)
        elif kind == b'IEND':
            if length or stop != len(payload):
                raise ValueError('PNG 结束块或尾部无效')
            ended = True
            break
        elif kind and not kind[0] & 32:
            raise ValueError('PNG 包含不支持的关键数据块')
        position = stop
    if not image or not ended or not compressed:
        raise ValueError('PNG 不完整，缺少像素数据或结束块')
    width, height, depth, color, compression, filtering, interlace = image
    depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
    if width < 2 or height < 2:
        raise ValueError('单像素或单行占位图不能作为表格预览')
    if color not in depths or depth not in depths[color] or compression or filtering or interlace not in (0, 1):
        raise ValueError('PNG 像素格式无效')
    if color == 3 and not palette:
        raise ValueError('索引 PNG 缺少调色板')
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    passes = [(0, 0, 1, 1)] if not interlace else [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8),
               (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
    rows = []
    for x, y, dx, dy in passes:
        columns = max(0, (width - x + dx - 1) // dx)
        count = max(0, (height - y + dy - 1) // dy)
        if columns and count:
            rows.append((count, 1 + (columns * channels * depth + 7) // 8))
    expected = sum(count * size for count, size in rows)
    if expected > 256 * 1024 * 1024:
        raise ValueError('PNG 像素数据过大，请分成正常缩放的局部预览')
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(bytes(compressed), expected + 1)
        if not decoder.eof or decoder.unused_data or len(raw) != expected:
            raise ValueError('PNG 像素数据长度无效或流不完整')
    except zlib.error as error:
        raise ValueError('PNG 像素数据无法解压') from error
    offset = 0
    for count, size in rows:
        for _ in range(count):
            if raw[offset] > 4:
                raise ValueError('PNG 行过滤标记无效')
            offset += size
    return width, height

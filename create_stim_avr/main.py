import yaml
import re


def item_parse(item: str) -> tuple[bytes, str]:
    item_bytes = bytes()

    data_type, *vals = item.split()
    m = re.match(r"(\w)(\d+)(?:(\[)?)(?:(\d+)\])?", data_type)

    if m is None or m.group(1) not in ("u", "i", "s"):
        raise TypeError(
            f"m is NoneType \"{data_type}\" not work, check yaml")

    if len(vals) == 0:
        vals.append("0")

    type_size = int(m.group(2)) // 8
    is_array = m.group(3) == "["
    array_len_str = m.group(4)

    match is_array, array_len_str:
        case False, None:
            array_len = 1
        case True, None:
            array_len = len(vals)
        case True, array_len_str:
            array_len = int(array_len_str)
        case _:
            raise TypeError(f"Type \"{data_type}\" not work, check yaml")

    if len(vals) > array_len:
        print(f"Warning: init for \"{item}\" long, the first value " +
              f"will be used")
        vals = vals[:array_len]

    item_bytes = bytes()
    for val in vals:
        v = int(val, 0)
        item_bytes += v.to_bytes(type_size, signed=(v < 0))
    delta = array_len - len(item_bytes)
    if delta > 0:
        item_bytes += bytes(delta)

    vals_str = " ".join(vals)
    return (item_bytes, f"{data_type} {vals_str}")


def pac_parse(pac: dict[str, str]) -> bytes:
    bb = bytes()
    for item_name in pac:
        b, new_item = item_parse(pac[item_name])
        bb += b
        pac[item_name] = new_item
    return bb


def append_stim_for_byte(strs: list[str], byte: int):
    set_bit = "PIND |= 0x01"
    clr_bit = "PIND &= 0xFE"
    delay = "#417"

    strs.append(f'''\
// Формирование байта 0x{byte:02X} {"-"*53}

// Старт бит
{clr_bit}
{delay}

// Данные\
''')

    for i in range(8):
        strs.append(set_bit if byte & (1 << i) else clr_bit)
        strs.append(delay)

    strs.append(f'''\

// Стоп бит
{set_bit}
{delay}

// Задержка после байта
{delay}
''')

    return strs


def append_package_bytes(strs: list[str], pac_bytes: bytes):
    if len(pac_bytes) <= 13:
        strs.append("// Посылка: " + " ".join(f"0x{b:02X}" for b in pac_bytes))
    else:
        strs.append("// Посылка:")
        tmp_strs = ["// " + " ".join(f"0x{b:02X}" for b in pac_bytes[i:i+15])
                    for i in range(0, len(pac_bytes), 15)]
        strs.extend(tmp_strs)

    return strs


def main():

    with open('package.yaml', 'r') as file:
        pacs = yaml.safe_load(file)

    for pac in pacs:
        pac_bytes = pac_parse(pacs[pac])

        stim_strs = []
        stim_strs.append(f"// {pac}:")
        for key, val in pacs[pac].items():
            stim_strs.append(f"//   {key}: {val}")
        stim_strs.append(f"// Количество байт: {len(pac_bytes)}")
        append_package_bytes(stim_strs, pac_bytes)
        stim_strs.append("")
        for byte in pac_bytes:
            append_stim_for_byte(stim_strs, byte)
        stim_str = '\n'.join(stim_strs)
        
        with open(f'{pac}.stim', 'w', encoding='utf-8') as file:
            file.write(stim_str)

        print(f"{pac}:")
        for key, val in pacs[pac].items():
            print(f"  {key}: {val}")
        print(f"Количество байт: {len(pac_bytes)}")
        print(f"Посылка: " + " ".join(f"0x{b:02X}" for b in pac_bytes))
        print()


if __name__ == "__main__":
    main()

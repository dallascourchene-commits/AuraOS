/* Exact minimal reproduction of the supplied Xhdv inline-assembly surface. */
#define OPCODE_CUSTOM0 0x0B

#define asm_hdv_bind(hd, hs1, hs2) \
    __asm__ volatile ( \
        ".insn r %0, 0x0, 0x00, x0, x0, x0\n\t" \
        : \
        : "i"(OPCODE_CUSTOM0) \
    )

#define HDV_BIND(hd, hs1, hs2) \
    __asm__ volatile ( \
        ".insn r 0x0B, 0x0, 0x00, x" #hd ", x" #hs1 ", x" #hs2 "\n\t" \
    )

void xhdv_broken_bind_fixture(void) {
    asm_hdv_bind(1, 2, 3);
}

void xhdv_numbered_bind_fixture(void) {
    HDV_BIND(1, 2, 3);
}

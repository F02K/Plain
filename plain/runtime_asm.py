"""The small runtime that every compiled Plain program contains.

It is plain NASM assembly (no hidden magic): a few helpers for text, lists,
memory and errors. The C library is only used for the operating system parts
(printing, reading a line, memory, number formatting).

Value model (every value is one 64-bit slot):
    number   -> 64-bit floating point number
    boolean  -> 0 or 1
    text     -> pointer to a zero terminated string
    thing    -> pointer to a block of slots, one per field
    list     -> pointer to [size, capacity, data pointer]
"""

HEADER = r"""
; ---- platform selection -------------------------------------------------
%ifdef WINDOWS
  %define A1 rcx
  %define A2 rdx
  %define A3 r8
  %define A4 r9
%else
  %define A1 rdi
  %define A2 rsi
  %define A3 rdx
  %define A4 rcx
%endif

default rel

; Enter a try block: remember where to continue if an error happens.
%macro TRY_ENTER 1
    mov rax, [rel rt_hcount]
    cmp rax, 1024
    jb %%ok
    lea A1, [rel rt_msg_try_deep]
    xor A2, A2
    call rt_error
%%ok:
    imul rcx, rax, 24
    lea rdx, [rel rt_handlers]
    add rdx, rcx
    mov [rdx], rsp
    mov [rdx + 8], rbp
    lea rcx, [rel %1]
    mov [rdx + 16], rcx
    inc rax
    mov [rel rt_hcount], rax
%endmacro
"""

RUNTIME = r"""
; ======================= runtime =========================================

; rt_alloc(bytes) -> zeroed memory
rt_alloc:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov A2, A1
    mov A1, 1
    call calloc
    test rax, rax
    jnz .ok
    lea A1, [rel rt_msg_oom]
    xor A2, A2
    call rt_error
.ok:
    leave
    ret

; rt_error(message, line): jump to the innermost 'catch', or stop the program
rt_error:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A1
    mov [rbp - 16], A2
    mov [rel rt_last_error], A1
    mov rax, [rel rt_hcount]
    test rax, rax
    jz .fatal
    dec rax
    mov [rel rt_hcount], rax
    imul rax, rax, 24
    lea rcx, [rel rt_handlers]
    add rcx, rax
    mov rsp, [rcx]
    mov rbp, [rcx + 8]
    jmp [rcx + 16]
.fatal:
    cmp qword [rbp - 16], 0
    je .noline
    lea A1, [rel rt_fmt_err_line]
    mov A2, [rbp - 16]
    xor eax, eax
    call printf
    jmp .msg
.noline:
    lea A1, [rel rt_fmt_err]
    xor eax, eax
    call printf
.msg:
    mov A1, [rbp - 8]
    call puts
    mov A1, 1
    call exit

; rt_say(text): print a line
rt_say:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    call puts
    xor A1, A1
    call fflush
    leave
    ret

; rt_num_to_text(number) -> text
rt_num_to_text:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A1
    mov A1, 40
    call rt_alloc
    mov [rbp - 16], rax
%ifdef WINDOWS
    mov rcx, rax
    mov rdx, 40
    lea r8, [rel rt_fmt_num]
    mov r9, [rbp - 8]
    movq xmm3, r9
%else
    mov rdi, rax
    mov rsi, 40
    lea rdx, [rel rt_fmt_num]
    movq xmm0, [rbp - 8]
    mov eax, 1
%endif
    call snprintf
    mov rax, [rbp - 16]
    leave
    ret

; rt_concat(a, b) -> new text
rt_concat:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A1
    mov [rbp - 16], A2
    call strlen
    mov [rbp - 24], rax
    mov A1, [rbp - 16]
    call strlen
    mov [rbp - 32], rax
    mov A1, [rbp - 24]
    add A1, rax
    add A1, 1
    call rt_alloc
    mov [rbp - 40], rax
    mov A1, rax
    mov A2, [rbp - 8]
    mov A3, [rbp - 24]
    call memcpy
    mov A1, [rbp - 40]
    add A1, [rbp - 24]
    mov A2, [rbp - 16]
    mov A3, [rbp - 32]
    add A3, 1
    call memcpy
    mov rax, [rbp - 40]
    leave
    ret

; rt_text_eq(a, b) -> 1 if equal else 0
rt_text_eq:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    call strcmp
    test eax, eax
    sete al
    movzx eax, al
    leave
    ret

; rt_input(prompt) -> text read from the keyboard (one line)
rt_input:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov A2, A1
    lea A1, [rel rt_fmt_input]
    xor eax, eax
    call printf
    xor A1, A1
    call fflush
    mov A1, 4096
    call rt_alloc
    mov [rbp - 8], rax
    mov qword [rbp - 16], 0
.loop:
    call getchar
    cmp eax, -1
    je .done
    cmp eax, 10
    je .done
    cmp eax, 13
    je .loop
    mov rcx, [rbp - 16]
    cmp rcx, 4094
    jae .loop
    mov rdx, [rbp - 8]
    mov [rdx + rcx], al
    inc rcx
    mov [rbp - 16], rcx
    jmp .loop
.done:
    mov rax, [rbp - 8]
    leave
    ret

; rt_input_number(prompt, line) -> number typed by the user
; Only digits, + - . e E and spaces are accepted; anything else is an error.
rt_input_number:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A2
    call rt_input
    mov [rbp - 16], rax
    mov rcx, rax
.scan:
    movzx eax, byte [rcx]
    test eax, eax
    jz .convert
    cmp al, ' '
    je .next
    cmp al, '+'
    je .next
    cmp al, '-'
    je .next
    cmp al, '.'
    je .next
    cmp al, 'e'
    je .next
    cmp al, 'E'
    je .next
    cmp al, '0'
    jb .bad
    cmp al, '9'
    ja .bad
.next:
    inc rcx
    jmp .scan
.convert:
    mov A1, [rbp - 16]
    lea A2, [rbp - 24]
    call strtod
    movq rax, xmm0
    mov [rbp - 32], rax
    mov rdx, [rbp - 24]
    cmp rdx, [rbp - 16]
    je .bad
.trail:
    cmp byte [rdx], ' '
    jne .check
    inc rdx
    jmp .trail
.check:
    cmp byte [rdx], 0
    jne .bad
    mov rax, [rbp - 32]
    leave
    ret
.bad:
    lea A1, [rel rt_msg_notnum]
    mov A2, [rbp - 8]
    call rt_error

; rt_mod(a, b) -> a mod b (numbers)
rt_mod:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    movq xmm0, A1
    movq xmm1, A2
    call fmod
    movq rax, xmm0
    leave
    ret

; rt_text_length(text) -> number of characters (UTF-8 aware)
rt_text_length:
    xor eax, eax
    mov rcx, A1
.loop:
    movzx edx, byte [rcx]
    test edx, edx
    jz .done
    and edx, 0xC0
    cmp edx, 0x80
    je .next
    inc rax
.next:
    inc rcx
    jmp .loop
.done:
    cvtsi2sd xmm0, rax
    movq rax, xmm0
    ret

; rt_text_case(text, upper) -> new text; only the letters a-z are changed
rt_text_case:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A1
    mov [rbp - 16], A2
    call strlen
    lea A1, [rax + 1]
    call rt_alloc
    mov [rbp - 24], rax
    mov rcx, [rbp - 8]
    mov rdx, rax
    mov r8, [rbp - 16]
.loop:
    movzx eax, byte [rcx]
    test eax, eax
    jz .done
    test r8, r8
    jz .lower
    cmp al, 'a'
    jb .store
    cmp al, 'z'
    ja .store
    sub al, 32
    jmp .store
.lower:
    cmp al, 'A'
    jb .store
    cmp al, 'Z'
    ja .store
    add al, 32
.store:
    mov [rdx], al
    inc rcx
    inc rdx
    jmp .loop
.done:
    mov rax, [rbp - 24]
    leave
    ret

; rt_text_part(text, start, count, line) -> new text (characters, the first is at 0)
rt_text_part:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A1
    mov [rbp - 32], A4
    movq xmm0, A2
    cvttsd2si rax, xmm0
    mov [rbp - 16], rax
    movq xmm0, A3
    cvttsd2si rax, xmm0
    mov [rbp - 24], rax
    cmp qword [rbp - 16], 0
    jl .neg
    cmp qword [rbp - 24], 0
    jl .neg
    mov A1, [rbp - 8]
    call strlen
    lea A1, [rax + 1]
    call rt_alloc
    mov [rbp - 40], rax
    mov rcx, [rbp - 8]
    mov rdx, [rbp - 16]
.skip:
    test rdx, rdx
    jz .take
    movzx eax, byte [rcx]
    test eax, eax
    jz .take
    inc rcx
.skipcont:
    movzx eax, byte [rcx]
    and eax, 0xC0
    cmp eax, 0x80
    jne .skipdone
    inc rcx
    jmp .skipcont
.skipdone:
    dec rdx
    jmp .skip
.take:
    mov r8, [rbp - 40]
    mov rdx, [rbp - 24]
.copy:
    test rdx, rdx
    jz .fin
    movzx eax, byte [rcx]
    test eax, eax
    jz .fin
    mov [r8], al
    inc rcx
    inc r8
.copycont:
    movzx eax, byte [rcx]
    mov r9d, eax
    and r9d, 0xC0
    cmp r9d, 0x80
    jne .copydone
    mov [r8], al
    inc rcx
    inc r8
    jmp .copycont
.copydone:
    dec rdx
    jmp .copy
.fin:
    mov rax, [rbp - 40]
    leave
    ret
.neg:
    lea A1, [rel rt_msg_textpos]
    mov A2, [rbp - 32]
    call rt_error

; rt_text_contains(text, piece) -> 1 if piece is inside text else 0
rt_text_contains:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    call strstr
    test rax, rax
    setne al
    movzx eax, al
    leave
    ret

; rt_random(low, high, line) -> whole number from low to high (both included)
rt_random:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    mov [rbp - 8], A3
    movq xmm0, A1
    cvttsd2si r8, xmm0
    movq xmm0, A2
    cvttsd2si r9, xmm0
    cmp r8, r9
    jle .ok
    lea A1, [rel rt_msg_random]
    mov A2, [rbp - 8]
    call rt_error
.ok:
    sub r9, r8
    inc r9
    mov rax, [rel rt_rng]
    test rax, rax
    jnz .step
    rdtsc
    shl rdx, 32
    or rax, rdx
    mov rcx, 0x9E3779B97F4A7C15
    imul rax, rcx
    or rax, 1
.step:
    mov rcx, rax
    shl rcx, 13
    xor rax, rcx
    mov rcx, rax
    shr rcx, 7
    xor rax, rcx
    mov rcx, rax
    shl rcx, 17
    xor rax, rcx
    mov [rel rt_rng], rax
    test r9, r9
    jz .raw
    xor edx, edx
    div r9
    mov rax, rdx
.raw:
    add rax, r8
    cvtsi2sd xmm0, rax
    movq rax, xmm0
    leave
    ret

; rt_list_add(list, value)
rt_list_add:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A1
    mov [rbp - 16], A2
    mov rax, [rbp - 8]
    mov rcx, [rax]
    cmp rcx, [rax + 8]
    jb .store
    mov rcx, [rax + 8]
    add rcx, rcx
    cmp rcx, 4
    jae .cap
    mov rcx, 4
.cap:
    mov [rax + 8], rcx
    shl rcx, 3
    mov A2, rcx
    mov A1, [rax + 16]
    call realloc
    test rax, rax
    jnz .grown
    lea A1, [rel rt_msg_oom]
    xor A2, A2
    call rt_error
.grown:
    mov rcx, [rbp - 8]
    mov [rcx + 16], rax
.store:
    mov rcx, [rbp - 8]
    mov rax, [rcx]
    mov rdx, [rcx + 16]
    lea rdx, [rdx + rax * 8]
    mov rax, [rbp - 16]
    mov [rdx], rax
    mov rax, [rcx]
    inc rax
    mov [rcx], rax
    leave
    ret

; rt_list_get(list, index, line) -> item
rt_list_get:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    cmp A2, [A1]
    jb .ok
    mov A2, A3
    lea A1, [rel rt_msg_index]
    call rt_error
.ok:
    mov rax, [A1 + 16]
    mov rax, [rax + A2 * 8]
    leave
    ret

; rt_list_set(list, index, value, line)
rt_list_set:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    cmp A2, [A1]
    jb .ok
    mov A2, A4
    lea A1, [rel rt_msg_index]
    call rt_error
.ok:
    mov rax, [A1 + 16]
    mov [rax + A2 * 8], A3
    leave
    ret

; rt_list_remove(list, value, is_text): remove the first matching item
rt_list_remove:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A1
    mov [rbp - 16], A2
    mov [rbp - 24], A3
    mov qword [rbp - 32], 0
.loop:
    mov rax, [rbp - 8]
    mov rcx, [rbp - 32]
    cmp rcx, [rax]
    jae .end
    mov rdx, [rax + 16]
    mov rdx, [rdx + rcx * 8]
    cmp qword [rbp - 24], 0
    je .raw
    mov A1, rdx
    mov A2, [rbp - 16]
    call strcmp
    test eax, eax
    jz .found
    jmp .next
.raw:
    cmp rdx, [rbp - 16]
    je .found
.next:
    inc qword [rbp - 32]
    jmp .loop
.found:
    mov rax, [rbp - 8]
    mov rcx, [rbp - 32]
    mov rdx, [rax + 16]
.shift:
    lea r8, [rcx + 1]
    cmp r8, [rax]
    jae .shrink
    mov r9, [rdx + r8 * 8]
    mov [rdx + rcx * 8], r9
    mov rcx, r8
    jmp .shift
.shrink:
    dec qword [rax]
.end:
    leave
    ret

; rt_list_remove_at(list, index, line)
rt_list_remove_at:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    cmp A2, [A1]
    jb .ok
    mov A2, A3
    lea A1, [rel rt_msg_index]
    call rt_error
.ok:
    mov rax, A1
    mov rcx, A2
    mov rdx, [rax + 16]
.shift:
    lea r8, [rcx + 1]
    cmp r8, [rax]
    jae .shrink
    mov r9, [rdx + r8 * 8]
    mov [rdx + rcx * 8], r9
    mov rcx, r8
    jmp .shift
.shrink:
    dec qword [rax]
    leave
    ret

; rt_list_contains(list, value, is_text) -> 1 if the list has the value else 0
rt_list_contains:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov [rbp - 8], A1
    mov [rbp - 16], A2
    mov [rbp - 24], A3
    mov qword [rbp - 32], 0
.loop:
    mov rax, [rbp - 8]
    mov rcx, [rbp - 32]
    cmp rcx, [rax]
    jae .no
    mov rdx, [rax + 16]
    mov rdx, [rdx + rcx * 8]
    cmp qword [rbp - 24], 0
    je .raw
    mov A1, rdx
    mov A2, [rbp - 16]
    call strcmp
    test eax, eax
    jz .yes
    jmp .next
.raw:
    cmp rdx, [rbp - 16]
    je .yes
.next:
    inc qword [rbp - 32]
    jmp .loop
.yes:
    mov eax, 1
    leave
    ret
.no:
    xor eax, eax
    leave
    ret

; rt_cmp_num / rt_cmp_text: comparison functions for qsort
rt_cmp_num:
    movq xmm0, [A1]
    movq xmm1, [A2]
    xor eax, eax
    ucomisd xmm0, xmm1
    seta al
    setb dl
    movzx edx, dl
    sub eax, edx
    ret

rt_cmp_text:
    sub rsp, 40
    mov A1, [A1]
    mov A2, [A2]
    call strcmp
    add rsp, 40
    ret

; rt_list_sort(list, is_text): sort the items, smallest first
rt_list_sort:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    mov rax, A1
    mov r10, A2
    mov A1, [rax + 16]
    mov A2, [rax]
    mov A3, 8
    lea A4, [rel rt_cmp_num]
    test r10, r10
    jz .go
    lea A4, [rel rt_cmp_text]
.go:
    call qsort
    leave
    ret
"""

DATA = r"""
rt_fmt_num:      db "%.15g", 0
rt_fmt_input:      db "%s ", 0
rt_fmt_err_line: db "Error in line %d: ", 0
rt_fmt_err:      db "Error: ", 0
rt_str_true:     db "true", 0
rt_str_false:    db "false", 0
rt_str_nothing:  db "nothing", 0
rt_msg_oom:      db "The computer ran out of memory.", 0
rt_msg_index:    db "That list position does not exist (the first item is at position 0).", 0
rt_msg_notnum:   db "That is not a number.", 0
rt_msg_div0:     db "Cannot divide by zero.", 0
rt_msg_mod0:     db "Cannot use mod with zero.", 0
rt_msg_try_deep: db "Too many nested try blocks.", 0
rt_msg_sqrt:     db "Cannot take the square root of a negative number.", 0
rt_msg_random:   db "The first number of 'random' must not be bigger than the second.", 0
rt_msg_textpos:  db "Text positions and lengths cannot be negative.", 0
"""

BSS = r"""
rt_hcount:     resq 1
rt_last_error: resq 1
rt_rng:        resq 1
rt_line:       resq 1
rt_handlers:   resq 3 * 1024
"""

EXTERNS_COMMON = ["calloc", "realloc", "printf", "puts", "snprintf", "strlen", "memcpy",
                  "strcmp", "getchar", "fflush", "exit", "fmod", "strtod", "strstr", "qsort"]

from .runtime_gfx import GFX_BSS, GFX_DATA, GFX_EXTERNS, GFX_RUNTIME  # noqa: E402,F401

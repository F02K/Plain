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

; rt_ask(prompt) -> text read from the keyboard (one line)
rt_ask:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    mov A2, A1
    lea A1, [rel rt_fmt_ask]
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
"""

DATA = r"""
rt_fmt_num:      db "%.15g", 0
rt_fmt_ask:      db "%s ", 0
rt_fmt_err_line: db "Error in line %d: ", 0
rt_fmt_err:      db "Error: ", 0
rt_str_true:     db "true", 0
rt_str_false:    db "false", 0
rt_str_nothing:  db "nothing", 0
rt_msg_oom:      db "The computer ran out of memory.", 0
rt_msg_index:    db "That list position does not exist (the first item is at position 0).", 0
rt_msg_div0:     db "Cannot divide by zero.", 0
rt_msg_mod0:     db "Cannot use mod with zero.", 0
rt_msg_try_deep: db "Too many nested try blocks.", 0
"""

BSS = r"""
rt_hcount:     resq 1
rt_last_error: resq 1
rt_handlers:   resq 3 * 1024
"""

EXTERNS_COMMON = ["calloc", "realloc", "printf", "puts", "snprintf", "strlen", "memcpy",
                  "strcmp", "getchar", "fflush", "exit", "fmod"]

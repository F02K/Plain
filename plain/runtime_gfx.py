"""Windows and drawing for the assembly backend (Win32, Windows target only).

Everything is drawn into an invisible bitmap (the back buffer); show() copies it to the
window. The Python backend does the same with tkinter (see GFX_PRELUDE in pyruntime.py).
Set the environment variable PLAIN_HEADLESS to keep windows hidden (used by the tests).
"""

GFX_EXTERNS = ["RegisterClassW", "CreateWindowExW", "ShowWindow", "DestroyWindow", "DefWindowProcW",
               "PeekMessageW", "GetMessageW", "DispatchMessageW", "PostQuitMessage", "GetDC", "ReleaseDC",
               "BeginPaint", "EndPaint", "AdjustWindowRect", "LoadCursorW", "FillRect", "GetAsyncKeyState",
               "GetForegroundWindow", "GetCursorPos", "ScreenToClient",
               "CreateCompatibleDC", "CreateCompatibleBitmap", "SelectObject", "DeleteObject",
               "CreateSolidBrush", "BitBlt", "Ellipse", "CreatePen", "MoveToEx", "LineTo", "SetTextColor",
               "SetBkMode", "TextOutW", "CreateFontW", "GetStockObject", "GetModuleHandleW",
               "MultiByteToWideChar", "Sleep", "getenv"]

GFX_RUNTIME = r"""
; ======================= windows (Win32) =====================================
%macro CLAMP255 1
    xor r10d, r10d
    test %1, %1
    cmovs %1, r10
    mov r10d, 255
    cmp %1, 255
    cmovg %1, r10
%endmacro

; stop with an error when no window was opened yet
rt_gfx_need:
    cmp qword [rel rt_gfx_memdc], 0
    jne .ok
    sub rsp, 40
    lea rcx, [rel rt_msg_nowin]
    mov rdx, [rel rt_line]
    call rt_error
.ok:
    ret

; rt_gfx_window(title, width, height)
rt_gfx_window:
    push rbp
    mov rbp, rsp
    sub rsp, 1328
    mov [rbp - 8], rcx
    movq xmm0, rdx
    cvttsd2si rax, xmm0
    mov [rbp - 16], rax
    movq xmm0, r8
    cvttsd2si rax, xmm0
    mov [rbp - 24], rax
    cmp qword [rel rt_gfx_open], 0
    je .fresh
    lea rcx, [rel rt_msg_winopen]
    mov rdx, [rel rt_line]
    call rt_error
.fresh:
    mov rax, [rbp - 16]
    cmp rax, 1
    jl .badsize
    cmp rax, 4000
    jg .badsize
    mov rax, [rbp - 24]
    cmp rax, 1
    jl .badsize
    cmp rax, 4000
    jg .badsize
    jmp .size_ok
.badsize:
    lea rcx, [rel rt_msg_winsize]
    mov rdx, [rel rt_line]
    call rt_error
.size_ok:
    mov ecx, 65001
    xor edx, edx
    mov r8, [rbp - 8]
    mov r9d, -1
    lea rax, [rbp - 1200]
    mov [rsp + 32], rax
    mov qword [rsp + 40], 512
    call MultiByteToWideChar
    xor ecx, ecx
    call GetModuleHandleW
    mov [rbp - 32], rax
    xor ecx, ecx
    mov edx, 32512
    call LoadCursorW
    mov qword [rbp - 160], 0
    lea rcx, [rel rt_gfx_wndproc]
    mov [rbp - 152], rcx
    mov qword [rbp - 144], 0
    mov rcx, [rbp - 32]
    mov [rbp - 136], rcx
    mov qword [rbp - 128], 0
    mov [rbp - 120], rax
    mov qword [rbp - 112], 0
    mov qword [rbp - 104], 0
    lea rcx, [rel rt_gfx_class]
    mov [rbp - 96], rcx
    lea rcx, [rbp - 160]
    call RegisterClassW
    mov dword [rbp - 64], 0
    mov dword [rbp - 60], 0
    mov rax, [rbp - 16]
    mov [rbp - 56], eax
    mov rax, [rbp - 24]
    mov [rbp - 52], eax
    lea rcx, [rbp - 64]
    mov edx, 0x00CA0000
    xor r8d, r8d
    call AdjustWindowRect
    xor ecx, ecx
    lea rdx, [rel rt_gfx_class]
    lea r8, [rbp - 1200]
    mov r9d, 0x00CA0000
    mov eax, 0x80000000
    mov [rsp + 32], rax
    mov [rsp + 40], rax
    mov eax, [rbp - 56]
    sub eax, [rbp - 64]
    mov [rsp + 48], rax
    mov eax, [rbp - 52]
    sub eax, [rbp - 60]
    mov [rsp + 56], rax
    mov qword [rsp + 64], 0
    mov qword [rsp + 72], 0
    mov rax, [rbp - 32]
    mov [rsp + 80], rax
    mov qword [rsp + 88], 0
    call CreateWindowExW
    test rax, rax
    jnz .created
    lea rcx, [rel rt_msg_winfail]
    mov rdx, [rel rt_line]
    call rt_error
.created:
    mov [rbp - 40], rax
    mov [rel rt_gfx_hwnd], rax
    mov rcx, rax
    call GetDC
    mov [rbp - 48], rax
    mov rcx, rax
    call CreateCompatibleDC
    mov [rel rt_gfx_memdc], rax
    mov rcx, [rbp - 48]
    mov rdx, [rbp - 16]
    mov r8, [rbp - 24]
    call CreateCompatibleBitmap
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, rax
    call SelectObject
    mov rcx, [rbp - 40]
    mov rdx, [rbp - 48]
    call ReleaseDC
    mov rax, [rbp - 16]
    mov [rel rt_gfx_w], rax
    mov rax, [rbp - 24]
    mov [rel rt_gfx_h], rax
    mov qword [rel rt_gfx_open], 1
    mov rcx, [rel rt_gfx_memdc]
    mov edx, 1
    call SetBkMode
    mov ecx, -20
    xor edx, edx
    xor r8d, r8d
    xor r9d, r9d
    mov qword [rsp + 32], 400
    mov qword [rsp + 40], 0
    mov qword [rsp + 48], 0
    mov qword [rsp + 56], 0
    mov qword [rsp + 64], 1
    mov qword [rsp + 72], 0
    mov qword [rsp + 80], 0
    mov qword [rsp + 88], 0
    mov qword [rsp + 96], 0
    lea rax, [rel rt_gfx_font]
    mov [rsp + 104], rax
    call CreateFontW
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, rax
    call SelectObject
    xor ecx, ecx
    call GetStockObject
    mov [rbp - 48], rax
    mov dword [rbp - 64], 0
    mov dword [rbp - 60], 0
    mov rax, [rbp - 16]
    mov [rbp - 56], eax
    mov rax, [rbp - 24]
    mov [rbp - 52], eax
    mov rcx, [rel rt_gfx_memdc]
    lea rdx, [rbp - 64]
    mov r8, [rbp - 48]
    call FillRect
    lea rcx, [rel rt_gfx_env]
    call getenv
    test rax, rax
    jz .visible
    mov qword [rel rt_gfx_headless], 1
    jmp .done
.visible:
    mov qword [rel rt_gfx_headless], 0
    mov rcx, [rbp - 40]
    mov edx, 5
    call ShowWindow
.done:
    leave
    ret

; rt_gfx_wndproc(hwnd, message, wparam, lparam): called by Windows
rt_gfx_wndproc:
    cmp edx, 0x10
    je .close
    cmp edx, 0x02
    je .destroy
    cmp edx, 0x0F
    je .paint
    cmp edx, 0x14
    je .erase
    jmp DefWindowProcW
.erase:
    mov eax, 1
    ret
.close:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    mov qword [rel rt_gfx_open], 0
    call DestroyWindow
    xor eax, eax
    leave
    ret
.destroy:
    sub rsp, 40
    xor ecx, ecx
    call PostQuitMessage
    add rsp, 40
    xor eax, eax
    ret
.paint:
    push rbp
    mov rbp, rsp
    sub rsp, 224
    mov [rbp - 16], rcx
    lea rdx, [rbp - 96]
    call BeginPaint
    mov [rbp - 8], rax
    cmp qword [rel rt_gfx_memdc], 0
    je .skip
    mov rcx, rax
    xor edx, edx
    xor r8d, r8d
    mov r9, [rel rt_gfx_w]
    mov rax, [rel rt_gfx_h]
    mov [rsp + 32], rax
    mov rax, [rel rt_gfx_memdc]
    mov [rsp + 40], rax
    mov qword [rsp + 48], 0
    mov qword [rsp + 56], 0
    mov qword [rsp + 64], 0x00CC0020
    call BitBlt
.skip:
    mov rcx, [rbp - 16]
    lea rdx, [rbp - 96]
    call EndPaint
    xor eax, eax
    leave
    ret

; rt_gfx_color(red, green, blue): numbers from 0 to 255
rt_gfx_color:
    movq xmm0, rcx
    cvttsd2si rax, xmm0
    CLAMP255 rax
    movq xmm0, rdx
    cvttsd2si rdx, xmm0
    CLAMP255 rdx
    movq xmm0, r8
    cvttsd2si r8, xmm0
    CLAMP255 r8
    shl rdx, 8
    shl r8, 16
    or rax, rdx
    or rax, r8
    mov [rel rt_gfx_color_value], rax
    ret

; rt_gfx_fill(left, top, right, bottom): fill a rectangle (whole numbers) with the current colour
rt_gfx_fill:
    push rbp
    mov rbp, rsp
    sub rsp, 64
    mov [rbp - 16], ecx
    mov [rbp - 12], edx
    mov [rbp - 8], r8d
    mov [rbp - 4], r9d
    mov rcx, [rel rt_gfx_color_value]
    call CreateSolidBrush
    mov [rbp - 24], rax
    mov rcx, [rel rt_gfx_memdc]
    lea rdx, [rbp - 16]
    mov r8, rax
    call FillRect
    mov rcx, [rbp - 24]
    call DeleteObject
    leave
    ret

rt_gfx_clear:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    call rt_gfx_need
    xor ecx, ecx
    xor edx, edx
    mov r8, [rel rt_gfx_w]
    mov r9, [rel rt_gfx_h]
    call rt_gfx_fill
    leave
    ret

; rt_gfx_rectangle(x, y, width, height)
rt_gfx_rectangle:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    call rt_gfx_need
    movq xmm0, rcx
    cvttsd2si rax, xmm0
    mov [rbp - 8], rax
    movq xmm0, rdx
    cvttsd2si rax, xmm0
    mov [rbp - 16], rax
    movq xmm0, r8
    cvttsd2si r10, xmm0
    movq xmm0, r9
    cvttsd2si r11, xmm0
    mov rcx, [rbp - 8]
    mov rdx, [rbp - 16]
    lea r8, [rcx + r10]
    lea r9, [rdx + r11]
    call rt_gfx_fill
    leave
    ret

; rt_gfx_circle(x, y, radius)
rt_gfx_circle:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    call rt_gfx_need
    movq xmm0, rcx
    cvttsd2si rax, xmm0
    mov [rbp - 8], rax
    movq xmm0, rdx
    cvttsd2si rax, xmm0
    mov [rbp - 16], rax
    movq xmm0, r8
    cvttsd2si rax, xmm0
    mov [rbp - 24], rax
    mov rcx, [rel rt_gfx_color_value]
    call CreateSolidBrush
    mov [rbp - 32], rax
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, rax
    call SelectObject
    mov [rbp - 40], rax
    mov ecx, 8
    call GetStockObject
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, rax
    call SelectObject
    mov [rbp - 48], rax
    mov rcx, [rel rt_gfx_memdc]
    mov rax, [rbp - 8]
    mov rdx, rax
    sub rdx, [rbp - 24]
    add rax, [rbp - 24]
    mov r9, rax
    mov rax, [rbp - 16]
    mov r8, rax
    sub r8, [rbp - 24]
    add rax, [rbp - 24]
    mov [rsp + 32], rax
    call Ellipse
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, [rbp - 48]
    call SelectObject
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, [rbp - 40]
    call SelectObject
    mov rcx, [rbp - 32]
    call DeleteObject
    leave
    ret

; rt_gfx_line(x1, y1, x2, y2)
rt_gfx_line:
    push rbp
    mov rbp, rsp
    sub rsp, 80
    call rt_gfx_need
    movq xmm0, rcx
    cvttsd2si rax, xmm0
    mov [rbp - 8], rax
    movq xmm0, rdx
    cvttsd2si rax, xmm0
    mov [rbp - 16], rax
    movq xmm0, r8
    cvttsd2si rax, xmm0
    mov [rbp - 24], rax
    movq xmm0, r9
    cvttsd2si rax, xmm0
    mov [rbp - 32], rax
    xor ecx, ecx
    mov edx, 2
    mov r8, [rel rt_gfx_color_value]
    call CreatePen
    mov [rbp - 40], rax
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, rax
    call SelectObject
    mov [rbp - 48], rax
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, [rbp - 8]
    mov r8, [rbp - 16]
    xor r9d, r9d
    call MoveToEx
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, [rbp - 24]
    mov r8, [rbp - 32]
    call LineTo
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, [rbp - 48]
    call SelectObject
    mov rcx, [rbp - 40]
    call DeleteObject
    leave
    ret

; rt_gfx_write(text, x, y)
rt_gfx_write:
    push rbp
    mov rbp, rsp
    sub rsp, 1152
    mov [rbp - 24], rcx
    movq xmm0, rdx
    cvttsd2si rax, xmm0
    mov [rbp - 8], rax
    movq xmm0, r8
    cvttsd2si rax, xmm0
    mov [rbp - 16], rax
    call rt_gfx_need
    mov ecx, 65001
    xor edx, edx
    mov r8, [rbp - 24]
    mov r9d, -1
    lea rax, [rbp - 1100]
    mov [rsp + 32], rax
    mov qword [rsp + 40], 512
    call MultiByteToWideChar
    dec eax
    jns .len_ok
    xor eax, eax
.len_ok:
    mov eax, eax
    mov [rbp - 32], rax
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, [rel rt_gfx_color_value]
    call SetTextColor
    mov rcx, [rel rt_gfx_memdc]
    mov rdx, [rbp - 8]
    mov r8, [rbp - 16]
    lea r9, [rbp - 1100]
    mov rax, [rbp - 32]
    mov [rsp + 32], rax
    call TextOutW
    leave
    ret

; rt_gfx_show(): handle window events, copy the picture to the window, wait for the next frame
rt_gfx_show:
    push rbp
    mov rbp, rsp
    sub rsp, 144
    call rt_gfx_need
.pump:
    lea rcx, [rbp - 64]
    xor edx, edx
    xor r8d, r8d
    xor r9d, r9d
    mov qword [rsp + 32], 1
    call PeekMessageW
    test eax, eax
    jz .present
    lea rcx, [rbp - 64]
    call DispatchMessageW
    jmp .pump
.present:
    cmp qword [rel rt_gfx_open], 0
    je .wait
    mov rcx, [rel rt_gfx_hwnd]
    call GetDC
    mov [rbp - 8], rax
    mov rcx, rax
    xor edx, edx
    xor r8d, r8d
    mov r9, [rel rt_gfx_w]
    mov rax, [rel rt_gfx_h]
    mov [rsp + 32], rax
    mov rax, [rel rt_gfx_memdc]
    mov [rsp + 40], rax
    mov qword [rsp + 48], 0
    mov qword [rsp + 56], 0
    mov qword [rsp + 64], 0x00CC0020
    call BitBlt
    mov rcx, [rel rt_gfx_hwnd]
    mov rdx, [rbp - 8]
    call ReleaseDC
.wait:
    mov ecx, 15
    call Sleep
    leave
    ret

; rt_gfx_running() -> true while the window is open
rt_gfx_running:
    sub rsp, 40
    call rt_gfx_need
    mov rax, [rel rt_gfx_open]
    add rsp, 40
    ret

rt_gfx_close_window:
    sub rsp, 40
    call rt_gfx_need
    cmp qword [rel rt_gfx_open], 0
    je .done
    mov qword [rel rt_gfx_open], 0
    mov rcx, [rel rt_gfx_hwnd]
    call DestroyWindow
.done:
    add rsp, 40
    ret

; rt_gfx_pressed(name) -> true while that key is held down in our window
rt_gfx_pressed:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    mov [rbp - 8], rcx
    call rt_gfx_need
    mov rcx, [rbp - 8]
    movzx eax, byte [rcx]
    test eax, eax
    jz .unknown
    cmp byte [rcx + 1], 0
    jne .named
    cmp al, 'a'
    jb .upper
    cmp al, 'z'
    ja .upper
    sub al, 32
.upper:
    cmp al, '0'
    jb .unknown
    cmp al, '9'
    jbe .have
    cmp al, 'A'
    jb .unknown
    cmp al, 'Z'
    ja .unknown
.have:
    movzx ecx, al
    jmp .check
.named:
    lea rax, [rel rt_keytable]
    mov [rbp - 16], rax
.next:
    mov rax, [rbp - 16]
    mov rcx, [rax]
    test rcx, rcx
    jz .unknown
    mov rdx, [rbp - 8]
    call strcmp
    test eax, eax
    jz .found
    add qword [rbp - 16], 16
    jmp .next
.found:
    mov rax, [rbp - 16]
    mov ecx, [rax + 8]
.check:
    mov [rbp - 24], rcx
    call GetForegroundWindow
    cmp rax, [rel rt_gfx_hwnd]
    jne .no
    mov rcx, [rbp - 24]
    call GetAsyncKeyState
    movzx eax, ax
    shr eax, 15
    leave
    ret
.no:
    xor eax, eax
    leave
    ret
.unknown:
    lea rcx, [rel rt_msg_key]
    mov rdx, [rel rt_line]
    call rt_error

; mouse position inside the window (whole numbers, 0 = left / top edge)
rt_gfx_mouse_x:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    call rt_gfx_need
    lea rcx, [rbp - 16]
    call GetCursorPos
    mov rcx, [rel rt_gfx_hwnd]
    lea rdx, [rbp - 16]
    call ScreenToClient
    cvtsi2sd xmm0, dword [rbp - 16]
    movq rax, xmm0
    leave
    ret

rt_gfx_mouse_y:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    call rt_gfx_need
    lea rcx, [rbp - 16]
    call GetCursorPos
    mov rcx, [rel rt_gfx_hwnd]
    lea rdx, [rbp - 16]
    call ScreenToClient
    cvtsi2sd xmm0, dword [rbp - 12]
    movq rax, xmm0
    leave
    ret

rt_gfx_mouse_down:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    call rt_gfx_need
    call GetForegroundWindow
    cmp rax, [rel rt_gfx_hwnd]
    jne .no
    mov ecx, 1
    call GetAsyncKeyState
    movzx eax, ax
    shr eax, 15
    leave
    ret
.no:
    xor eax, eax
    leave
    ret

; rt_gfx_finish(): when the program ends, keep the window until the user closes it
rt_gfx_finish:
    push rbp
    mov rbp, rsp
    sub rsp, 96
    cmp qword [rel rt_gfx_headless], 0
    jne .end
.loop:
    cmp qword [rel rt_gfx_open], 0
    je .end
    lea rcx, [rbp - 64]
    xor edx, edx
    xor r8d, r8d
    xor r9d, r9d
    call GetMessageW
    test eax, eax
    jle .end
    lea rcx, [rbp - 64]
    call DispatchMessageW
    jmp .loop
.end:
    leave
    ret
"""

GFX_DATA = r"""
rt_gfx_class:    dw 'P','l','a','i','n','W','i','n','d','o','w',0
rt_gfx_font:     dw 'S','e','g','o','e',' ','U','I',0
rt_gfx_env:      db "PLAIN_HEADLESS", 0
rt_msg_nowin:    db "Open a window first, for example: window(", 34, "My game", 34, ", 640, 480).", 0
rt_msg_winopen:  db "A window is already open.", 0
rt_msg_winsize:  db "The window size must be between 1 and 4000.", 0
rt_msg_winfail:  db "I could not open the window.", 0
rt_msg_key:      db "I do not know that key. Use left, right, up, down, space, enter, escape, shift, ctrl, tab, backspace, a-z or 0-9.", 0
rt_k_left:       db "left", 0
rt_k_right:      db "right", 0
rt_k_up:         db "up", 0
rt_k_down:       db "down", 0
rt_k_space:      db "space", 0
rt_k_enter:      db "enter", 0
rt_k_escape:     db "escape", 0
rt_k_shift:      db "shift", 0
rt_k_ctrl:       db "ctrl", 0
rt_k_tab:        db "tab", 0
rt_k_backspace:  db "backspace", 0
align 8
rt_keytable:
    dq rt_k_left, 0x25
    dq rt_k_right, 0x27
    dq rt_k_up, 0x26
    dq rt_k_down, 0x28
    dq rt_k_space, 0x20
    dq rt_k_enter, 0x0D
    dq rt_k_escape, 0x1B
    dq rt_k_shift, 0x10
    dq rt_k_ctrl, 0x11
    dq rt_k_tab, 0x09
    dq rt_k_backspace, 0x08
    dq 0, 0
"""

GFX_BSS = r"""
rt_gfx_hwnd:        resq 1
rt_gfx_memdc:       resq 1
rt_gfx_w:           resq 1
rt_gfx_h:           resq 1
rt_gfx_open:        resq 1
rt_gfx_headless:    resq 1
rt_gfx_color_value: resq 1
"""

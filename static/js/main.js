// Sistema de Seguridad: Auto-Logout por Inactividad (3 Minutos)
function initInactivityTimer(logoutUrl) {
    let time;
    const timeout = 180000; // 3 minutos en milisegundos

    window.onload = resetTimer;
    document.onmousemove = resetTimer;
    document.onkeypress = resetTimer;
    document.ontouchstart = resetTimer;
    document.onclick = resetTimer;
    document.onscroll = resetTimer;

    function logout() {
        window.location.href = logoutUrl + "?timeout=true";
    }

    function resetTimer() {
        clearTimeout(time);
        time = setTimeout(logout, timeout);
    }
}

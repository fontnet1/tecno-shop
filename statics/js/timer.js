function updateTimer() {

    const timer = document.getElementById("otp-timer");
    const resendForm = document.getElementById("resend-form");
    const timerText = document.getElementById("timer-text");

    const now = Math.floor(Date.now() / 1000);

    const remain = expireTime - now;

    if (remain <= 0) {

        timer.style.display = "none";

        resendForm.style.display = "block";

        return;
    }

    const min = String(Math.floor(remain / 60)).padStart(2, "0");
    const sec = String(remain % 60).padStart(2, "0");

    timerText.innerHTML =
        `Resend code in <strong>${min}:${sec}</strong>`;
}

updateTimer();

setInterval(updateTimer,1000);
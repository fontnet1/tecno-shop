// ===== OTP Input Behavior =====
const otpInputs = document.querySelectorAll('.otp-input');

otpInputs.forEach((input, index) => {
  input.addEventListener('input', (e) => {
    const val = e.target.value.replace(/[^0-9]/g, '');
    e.target.value = val;

    if (val.length === 1) {
      e.target.classList.add('filled');
      const next = e.target.nextElementSibling;
      if (next && next.classList.contains('otp-input')) {
        next.focus();
      }
    } else {
      e.target.classList.remove('filled');
    }
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace') {
      if (e.target.value === '' || e.target.value.length === 0) {
        const prev = e.target.previousElementSibling;
        if (prev && prev.classList.contains('otp-input')) {
          prev.focus();
          prev.value = '';
          prev.classList.remove('filled');
        }
      } else {
        e.target.classList.remove('filled');
      }
    }

    if (e.key === 'ArrowLeft') {
      const prev = e.target.previousElementSibling;
      if (prev && prev.classList.contains('otp-input')) {
        prev.focus();
      }
    }
    if (e.key === 'ArrowRight') {
      const next = e.target.nextElementSibling;
      if (next && next.classList.contains('otp-input')) {
        next.focus();
      }
    }

    if (e.key === 'Enter') {
      e.preventDefault();
      const verifyBtn = document.querySelector('.btn-primary');
      if (verifyBtn) verifyBtn.click();
    }
  });

  input.addEventListener('focus', () => {
    input.select();
  });

  input.addEventListener('paste', (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/[^0-9]/g, '');
    if (pastedData.length >= 6) {
      otpInputs.forEach((inp, i) => {
        if (i < 6) {
          inp.value = pastedData[i];
          inp.classList.add('filled');
        }
      });
      otpInputs[5].focus();
    } else {
      for (let i = 0; i < pastedData.length; i++) {
        const targetIndex = index + i;
        if (targetIndex < 6) {
          otpInputs[targetIndex].value = pastedData[i];
          otpInputs[targetIndex].classList.add('filled');
        }
      }
      const focusIndex = Math.min(index + pastedData.length, 5);
      otpInputs[focusIndex].focus();
    }
  });
});


// ===== Resend Code =====
function resendCode(e) {
  e.preventDefault();
  const form = document.getElementById('resend-form');
  if (form) {
    form.submit();
  }
}


// ===== Submit OTP Form =====
const otpForm = document.getElementById("otp-form");

if (otpForm) {
  otpForm.addEventListener("submit", function (e) {
    const inputs = document.querySelectorAll(".otp-input");
    const hiddenInput = document.getElementById("otp-hidden");
    const verifyBtn = document.getElementById("verify-btn");

    if (!hiddenInput) return;

    const code = [...inputs].map(input => input.value.trim()).join("");

    if (code.length !== 6) {
      e.preventDefault();

      inputs.forEach(input => {
        if (!input.value.trim()) {
          input.classList.add("error");
          setTimeout(() => {
            input.classList.remove("error");
          }, 500);
        }
      });

      const firstEmpty = [...inputs].find(input => !input.value.trim());
      if (firstEmpty) {
        firstEmpty.focus();
      }
      return;
    }

    hiddenInput.value = code;

    if (verifyBtn) {
      verifyBtn.disabled = true;
      verifyBtn.textContent = "Verifying...";
    }
  });
}

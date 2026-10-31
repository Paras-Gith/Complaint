// Client-side validation (Bootstrap) + auto-dismiss flash messages
document.querySelectorAll('.needs-validation').forEach(form => {
  form.addEventListener('submit', e => {
    if (!form.checkValidity()) { e.preventDefault(); e.stopPropagation(); }
    form.classList.add('was-validated');
  });
});
setTimeout(() => {
  document.querySelectorAll('.alert-dismissible').forEach(a => bootstrap.Alert.getOrCreateInstance(a).close());
}, 6000);

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

  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  document.querySelectorAll('form[method="post" i]').forEach(f => {
    const i = document.createElement('input');
    i.type = 'hidden'; i.name = '_csrf'; i.value = csrf; f.appendChild(i);
  });
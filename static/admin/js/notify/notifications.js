document.addEventListener('DOMContentLoaded', () => {
  // تابع نمایش اعلان
  function showNotify(type, title, message, url) {
    $.notify(
      { title: `<strong>${title}</strong>`, message },
      {
        type,
        delay: 3000,
        placement: { from: 'top', align: 'left' },
        allow_dismiss: true,
        onClose: function() { if (url) window.location = url; }
      }
    );
  }

  // اگر در Context شمارش جدید باشد، اعلان نشان بده
  const rolesCount = parseInt('{{ pending_roles_count }}', 10);
  if (rolesCount > 0) {
    showNotify(
      'info',
      'درخواست جدید نقش',
      `شما ${rolesCount} درخواست جدید عضویت دارید.`,
      '{% url "unit_admin:role_list" %}'
    );
  }

  const ticketsCount = parseInt('{{ pending_tickets_count }}', 10);
  if (ticketsCount > 0) {
    showNotify(
      'warning',
      'تیکت جدید',
      `شما ${ticketsCount} تیکت در انتظار پاسخ دارید.`,
      '{% url "unit_admin:contact_list" %}'
    );
  }
});

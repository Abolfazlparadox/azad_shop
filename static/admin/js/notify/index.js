'use strict';
var notify = $.notify('<i class="fas fa-bell"></i></i><strong>لطفا صبر کنید :</strong> این برگه را نبندید', {
    type: 'theme',
    allow_dismiss: true,
    delay: 4000,
    showProgressbar: true,
    timer: 300,
    // timer: 555555500,
    animate: {
        enter: 'animated fadeInDown',
        exit: 'animated fadeOutUp'
    }
});

setTimeout(function () {
    notify.update('message', '<i class="fas fa-bell"></i></i><strong>لطفا صبر کنید.</strong> بارگذاری محتوا');
}, 1000);
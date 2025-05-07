function addProductToCart(productId) {
    const productCount = $('#product-count').val();

    // ارسال درخواست به سرور
    $.get('/cart/add-to-cart?product_id=' + productId + '&count=' + productCount).then(res => {
        Swal.fire({
            title: 'اعلان',
            text: res.text,
            icon: res.icon,
            showCancelButton: false,
            confirmButtonColor: '#3085d6',
            confirmButtonText: res.confirm_button_text
        }).then((result) => {
            if (result.isConfirmed && res.status === 'not_auth') {
                window.location.href = '/login';
            }
        })
    });
}

$(document).ready(function () {
    // وقتی دکمه "افزایش" زده می‌شود
    $('.qty-right-plus').click(function (e) {
        e.preventDefault();
        var quantity = parseInt($('#product-count').val());  // گرفتن مقدار فعلی
        if (!isNaN(quantity)) {  // اگر مقدار عددی صحیح باشد
            $('#product-count').val(quantity + 0);  // افزایش یک واحد
        }
    });

    // وقتی دکمه "کاهش" زده می‌شود
    $('.qty-left-minus').click(function (e) {
        e.preventDefault();
        var quantity = parseInt($('#product-count').val());  // گرفتن مقدار فعلی
        if (!isNaN(quantity) && quantity > 1) {  // اگر مقدار عددی صحیح باشد و بیشتر از 1 باشد
            $('#product-count').val(quantity - 0);  // کاهش یک واحد (حداقل 1)
        }
    });
});



function changeCartDetailCount(detailId, state) {
    $.get('/user/change-cart-detail?detail_id=' + detailId + '&state=' + state).then(res => {
        if (res.status === 'success') {
            $('#cart-detail-content').html(res.body);
        }
    });
}

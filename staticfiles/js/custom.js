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


function formatPriceWithCommas(amount) {
    amount = Number(amount);
    return amount.toLocaleString('en-us') + ' تومان';
}

function changeCartDetailCount(detailId, state) {
    $.get('/cart/change-cart-detail/?detail_id=' + detailId + '&state=' + state)
        .done(function (res) {
            const countInput = $('#count-input-' + detailId);

            if (res.status === 'success') {
                // بروزرسانی تعداد از سمت سرور
                countInput.val(res.count);

                // بروزرسانی قیمت‌ها با فرمت
                $('#total-price-' + detailId).text(formatPriceWithCommas(res.total_price));
                $('#total-cart-price').text(formatPriceWithCommas(res.total_cart_price));

            } else if (res.status === 'invalid_count') {
                Swal.fire({
                    title: 'خطا',
                    text: res.message,
                    icon: 'warning',
                    confirmButtonText: 'باشه'
                });

                // بازگرداندن مقدار معتبر و قیمت‌ها
                countInput.val(res.count);
                $('#total-price-' + detailId).text(formatPriceWithCommas(res.total_price));
                $('#total-cart-price').text(formatPriceWithCommas(res.total_cart_price));

            } else {
                alert('خطا در به‌روزرسانی تعداد');
            }
        })
        .fail(function () {
            alert('خطا در ارتباط با سرور');
        });
}

// function changeCartDetailCount(detailId, state) {
//     $.get('/cart/change-cart-detail/?detail_id=' + detailId + '&state=' + state)
//         .done(function (res) {
//             if (res.status === 'success') {
//                 // به‌روزرسانی قیمت محصول خاص
//                 $('#total-price-' + detailId).text(res.total_price);
//
//                 // به‌روزرسانی قیمت کل سبد خرید (در صورتی که لازم باشد)
//                 $('#total-cart-price').text(res.total_cart_price);
//             } else {
//                 alert('خطا در به‌روزرسانی تعداد');
//             }
//         })
//         .fail(function () {
//             alert('خطا در ارتباط با سرور');
//         });
// }

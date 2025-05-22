document.addEventListener('DOMContentLoaded', function () {
    const variantEl = document.getElementById('variant-data');
    if (!variantEl) return; // فقط در صفحه محصول اجرا شود


    const variantMap = JSON.parse(variantEl.textContent);
    let selectedAttributes = {};

    // انتخاب اولیه: اولین رنگ
    const colorInputs = document.querySelectorAll('.select-package[data-type="رنگ"] input[type="radio"]');
    if (colorInputs.length > 0) {
        colorInputs[0].checked = true;
        selectedAttributes['رنگ'] = colorInputs[0].dataset.value;
    }

    // انتخاب اولیه: سایر ویژگی‌ها
    document.querySelectorAll('.select-package:not([data-type="رنگ"])').forEach(group => {
        const type = group.dataset.type;
        const firstOption = group.querySelector('a');
        if (firstOption) {
            selectedAttributes[type] = firstOption.dataset.value;
        }
    });

    updateOtherAttributes(true);
    updatePriceStock();
    updateActiveStates();

    // وقتی رنگ تغییر می‌کند
    colorInputs.forEach(input => {
        input.addEventListener('change', function () {
            selectedAttributes['رنگ'] = this.dataset.value;

            // پاک کردن سایر ویژگی‌ها
            Object.keys(selectedAttributes).forEach(key => {
                if (key !== 'رنگ') delete selectedAttributes[key];
            });

            updateOtherAttributes(true);
            updatePriceStock();
            updateActiveStates();
        });
    });

    // کلیک روی ویژگی‌های غیر رنگ
    document.querySelectorAll('.select-package:not([data-type="رنگ"]) a').forEach(a => {
        a.addEventListener('click', function (e) {
            e.preventDefault();
            const type = this.dataset.type;
            const value = this.dataset.value;

            if (selectedAttributes[type] === value) {
                delete selectedAttributes[type];
            } else {
                selectedAttributes[type] = value;
            }

            updatePriceStock();
            updateActiveStates();
        });
    });

    function updateOtherAttributes(isInitial = false) {
        if (!selectedAttributes['رنگ']) return;

        const filteredVariants = Object.entries(variantMap).filter(([key]) =>
            key.includes(`رنگ:${selectedAttributes['رنگ']}`)
        );

        const attributeOptions = {};
        filteredVariants.forEach(([key]) => {
            const attrs = key.split(',');
            attrs.forEach(pair => {
                const [k, v] = pair.split(':');
                if (!attributeOptions[k]) attributeOptions[k] = new Set();
                attributeOptions[k].add(v);
            });
        });

        document.querySelectorAll('.select-package').forEach(group => {
            const type = group.dataset.type;
            if (type === 'رنگ') return;

            const allowedValues = attributeOptions[type] || new Set();
            group.querySelectorAll('a').forEach(a => {
                const value = a.dataset.value;
                if (allowedValues.has(value)) {
                    a.style.display = 'inline-block';
                    a.classList.remove('disabled');
                } else {
                    a.style.display = 'none';
                    a.classList.remove('active');
                    if (selectedAttributes[type] === value) {
                        delete selectedAttributes[type];
                    }
                }
            });

            const hasVisibleOption = [...group.querySelectorAll('a')].some(a => a.style.display !== 'none');
            const titleElement = group.previousElementSibling;

            if (titleElement && titleElement.classList.contains('product-title')) {
                if (hasVisibleOption) {
                    group.style.display = 'block';
                    titleElement.style.display = 'block';
                } else {
                    group.style.display = 'none';
                    titleElement.style.display = 'none';
                    if (selectedAttributes[type]) {
                        delete selectedAttributes[type];
                    }
                }
            }

            if (isInitial && hasVisibleOption && !selectedAttributes[type]) {
                const firstVisible = [...group.querySelectorAll('a')].find(a => a.style.display !== 'none');
                if (firstVisible) {
                    selectedAttributes[type] = firstVisible.dataset.value;
                }
            }
        });

        updateActiveStates();
    }

    function updatePriceStock() {
        const selectedKey = Object.keys(selectedAttributes)
            .map(k => `${k}:${selectedAttributes[k]}`)
            .sort()
            .join(',');

        const variant = variantMap[selectedKey];

        const selectedPriceElem = document.getElementById('selected-price');
        const selectedStockElem = document.getElementById('selected-stock');
        const originalPriceElem = document.getElementById('original-price');
        const discountContainer = document.getElementById('discount-container');
        const discountElem = document.getElementById('discount-percent');

        if (variant) {
            if (selectedPriceElem) selectedPriceElem.textContent = variant.price.toLocaleString() + ' تومان';
            if (selectedStockElem) selectedStockElem.textContent = variant.stock;

            if (variant.original_price && variant.original_price > variant.price) {
                if (originalPriceElem) {
                    originalPriceElem.textContent = variant.original_price.toLocaleString() + ' تومان';
                    originalPriceElem.style.display = 'inline';
                }
            } else {
                if (originalPriceElem) originalPriceElem.style.display = 'none';
            }

            if (variant.discount_percent && variant.discount_percent > 0) {
                if (discountElem) discountElem.textContent = `(${variant.discount_percent}% تخفیف)`;
                if (discountContainer) discountContainer.style.display = 'inline';
            } else {
                if (discountContainer) discountContainer.style.display = 'none';
            }
        } else {
            if (selectedPriceElem) selectedPriceElem.textContent = '—';
            if (selectedStockElem) selectedStockElem.textContent = '—';
            if (originalPriceElem) originalPriceElem.style.display = 'none';
            if (discountContainer) discountContainer.style.display = 'none';
        }
    }

    function updateActiveStates() {
        document.querySelectorAll('.select-package[data-type="رنگ"] input[type="radio"]').forEach(input => {
            input.checked = (selectedAttributes['رنگ'] === input.dataset.value);
        });

        document.querySelectorAll('.select-package:not([data-type="رنگ"]) a').forEach(a => {
            const type = a.dataset.type;
            const value = a.dataset.value;
            if (selectedAttributes[type] === value) {
                a.classList.add('active');
            } else {
                a.classList.remove('active');
            }
        });
    }
});






let variantData = null;  // تعریف متغیر بیرون از ready برای دسترسی در تمام توابع

// فرمت نمایش قیمت با جداکننده هزارگان و حذف اعشار
function formatPriceWithCommas(amount) {
    amount = Math.round(Number(amount));  // گرد کردن به عدد صحیح نزدیک
    return amount.toLocaleString('en') + ' تومان';
}

// بارگذاری انتخاب‌های پیش‌فرض (طبق کلاس active)
function loadSelectedAttributes() {
    selectedAttributes = {}; // خالی کردن
    $('.select-package').each(function () {
        const selected = $(this).find('[data-type].active');
        if (selected.length) {
            const type = selected.data('type');
            const value = selected.data('value');
            selectedAttributes[type] = value;
        }
    });
    // آپدیت اطلاعات variant با تعداد فعلی بعد از بارگذاری
    const quantity = parseInt($('#product-count').val()) || 1;
    updateVariantInfo(quantity);
}

// به‌روزرسانی اطلاعات variant بر اساس انتخاب‌های فعلی و تعداد
function updateVariantInfo(quantity = 1) {
        console.log('updateVariantInfo called with quantity:', quantity, 'and selectedAttributes:', selectedAttributes);

    if (!variantData) {
        // اگر داده variantData نیست، اطلاعات رو خالی کن و از تابع خارج شو
        $('#selected-price').text('—');
        $('#selected-stock').text('—');
        $('#original-price').hide();
        $('#discount-container').hide();
        $('#discount-percent').parent().hide();
        console.warn('variantData is null or undefined');
        return;
    }

    const keys = Object.keys(selectedAttributes).sort();
    const variantKey = keys.map(key => `${key}:${selectedAttributes[key]}`).join(',');
    console.log('Looking for variantKey:', variantKey);
    const variant = variantData[variantKey];

    if (variant) {
        console.log('Variant found:', variant);
        const totalPrice = variant.price * quantity;
        $('#selected-price').text(formatPriceWithCommas(totalPrice));
        $('#selected-stock').text(variant.stock);

        if (variant.discount_percent > 0) {
            const originalTotalPrice = variant.original_price * quantity;
            $('#original-price').text(formatPriceWithCommas(originalTotalPrice)).show();
            $('#discount-percent').text(`${variant.discount_percent}٪`).parent().show();

            const totalDiscount = (variant.original_price - variant.price) * quantity;
            if (totalDiscount > 0) {
                $('#total-discount').text(formatPriceWithCommas(totalDiscount));
                $('#discount-container').show();
            } else {
                $('#total-discount').text('');
                $('#discount-container').hide();
            }
        } else {
            $('#original-price').hide();
            $('#discount-container').hide();
            $('#discount-percent').parent().hide();
        }
    } else {
        console.warn('Variant not found for key:', variantKey);
        $('#selected-price').text('—');
        $('#selected-stock').text('—');
        $('#original-price').hide();
        $('#discount-container').hide();
        $('#discount-percent').parent().hide();
    }
}

// ذخیره انتخاب‌های فعلی کاربر برای ویژگی‌ها (مثلاً رنگ: قرمز، سایز: L)
let selectedAttributes = {};

// وقتی روی یک ویژگی (مثل رنگ یا سایز) کلیک می‌شود
$(document).on('click', '.select-package [data-type]', function () {
    const type = $(this).data('type');
    const value = $(this).data('value');

    // به‌روزرسانی ویژگی انتخاب‌شده
    selectedAttributes[type] = value;
        console.log('selectedAttributes updated:', selectedAttributes);


    // مشخص کردن وضعیت انتخاب‌شده در رابط کاربری
    const $parent = $(this).closest('.select-package');
    $parent.find('[data-type]').removeClass('active');
    $(this).addClass('active');

    // به‌روزرسانی اطلاعات variant بر اساس تعداد فعلی
    const quantity = parseInt($('#product-count').val()) || 1;
    updateVariantInfo(quantity);
});








// تابع افزودن محصول به سبد خرید
function addProductToCart(productId) {
    const productCount = parseInt($('#product-count').val()) || 1;

    const keys = Object.keys(selectedAttributes).sort();
    const variantKey = keys.map(key => `${key}:${selectedAttributes[key]}`).join(',');
    const variant = variantData[variantKey];

    if (!variant) {
        Swal.fire({
            title: 'خطا',
            text: 'لطفاً یک ترکیب ویژگی معتبر (مثل رنگ و سایز) را انتخاب کنید.',
            icon: 'warning',
            confirmButtonText: 'باشه'
        });
        return;
    }

    const selectedVariantId = variant.variant_id;

    $.get('/cart/add-to-cart', {
        product_id: productId,
        variant_id: selectedVariantId,
        count: productCount
    }).then(res => {
        Swal.fire({
            title: 'اعلان',
            text: res.text,
            icon: res.icon,
            confirmButtonColor: '#3085d6',
            confirmButtonText: res.confirm_button_text
        }).then((result) => {
            if (result.isConfirmed && res.status === 'not_auth') {
                window.location.href = '/login';
            }
        });
    });
}

// تغییر تعداد سبد خرید در صفحه سبد
function changeCartDetailCount(detailId, state) {
    $.get('/cart/change-cart-detail/', {
        detail_id: detailId,
        state: state
    }).done(function (res) {
        const countInput = $('#count-input-' + detailId);

        if (res.status === 'success' || res.status === 'invalid_count') {
            countInput.val(res.count);
            $('#total-price-' + detailId).text(formatPriceWithCommas(res.total_price));
            $('#total-cart-price').text(formatPriceWithCommas(res.total_cart_price));

            // نمایش سود کل در هر ردیف (در صورت وجود)
            const discountEl = $('#total-discount-' + detailId);
            if (discountEl.length && res.total_discount && res.total_discount > 0) {
                discountEl.text(formatPriceWithCommas(res.total_discount));
                discountEl.closest('[id^="discount-wrapper-"]').show();
            } else if (discountEl.length) {
                discountEl.text('');
                discountEl.closest('[id^="discount-wrapper-"]').hide();
            }

            if (res.status === 'invalid_count') {
                Swal.fire({
                    title: 'خطا',
                    text: res.message,
                    icon: 'warning',
                    confirmButtonText: 'باشه'
                });
            }
        } else {
            alert('خطا در به‌روزرسانی تعداد');
        }
    }).fail(function () {
        alert('خطا در ارتباط با سرور');
    });
}

$(document).ready(function () {
    // مقداردهی variantData پس از بارگذاری DOM
    const variantEl = document.getElementById('variant-data');
    variantData = variantEl ? JSON.parse(variantEl.textContent) : null;
    console.log('variantData loaded:', variantData);

    // بارگذاری انتخاب‌های پیش‌فرض از UI
    loadSelectedAttributes();

    // مقدار اولیه تعداد
    let quantity = parseInt($('#product-count').val()) || 1;

    // به‌روزرسانی اطلاعات variant
    updateVariantInfo(quantity);

    // مخفی کردن تخفیف‌های صفر
    $('[id^="discount-wrapper-"]').each(function () {
        const discountText = $(this).find('span').text();
        const discountNumber = Number(discountText.replace(/[^\d.-]/g, ''));
        if (discountNumber === 0) {
            $(this).hide();
        } else {
            $(this).show();
        }
    });

    // جلوگیری از دوباره‌بایند شدن کلیک‌ها
    $('.qty-right-plus').off('click').on('click', function (e) {
        e.preventDefault();
        let quantity = parseInt($('#product-count').val()) || 1;
        quantity += 1;
        $('#product-count').val(quantity);
        console.log('quantity increased:', quantity);
        updateVariantInfo(quantity);
    });

    $('.qty-left-minus').off('click').on('click', function (e) {
        e.preventDefault();
        let quantity = parseInt($('#product-count').val()) || 1;
        if (quantity > 1) {
            quantity -= 1;
            $('#product-count').val(quantity);
             console.log('quantity decreased:', quantity);
            updateVariantInfo(quantity);
        }
    });
});



document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('#checkout-form');
    if (!form) {
        return;
    }
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken'), // حتما ارسال CSRF
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            Swal.fire({
                title: data.success ? 'موفقیت' : 'خطا',
                text: data.message || (data.success ? 'سفارش با موفقیت ثبت شد.' : 'خطایی رخ داده است.'),
                icon: data.success ? 'success' : 'error',
                confirmButtonColor: '#3085d6',
                confirmButtonText: 'باشه'
            }).then((result) => {
                if (result.isConfirmed) {
                    if (data.status === 'not_auth') {
                        window.location.href = '/login';
                    } else if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    }
                }
            });
        })
        .catch(error => {
            console.error('خطای ارسال درخواست:', error);
            Swal.fire({
                title: 'خطا',
                text: 'خطایی در ارسال درخواست رخ داده است.',
                icon: 'error',
                confirmButtonColor: '#d33',
                confirmButtonText: 'باشه'
            });
        });
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

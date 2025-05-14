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


document.addEventListener("DOMContentLoaded", function () {
  const productVariantMap = JSON.parse(
    document.getElementById("product-variant-map-data").textContent
  );

  document.querySelectorAll(".product-package").forEach((pkg) => {
    const productId = pkg.dataset.productId;
    const productData = productVariantMap[productId];

    if (!productData) {
      console.error(`داده‌های محصول با شناسه ${productId} پیدا نشد`);
      return;
    }

    const colorInputs = pkg.querySelectorAll(`input[name="color-${productId}"]`);
    const sizeInputs = pkg.querySelectorAll(`input[name="size-${productId}"]`);
    const priceContainer = document.getElementById(`price-${productId}`);
    const stockContainer = document.getElementById(`stock-${productId}`);

    // اگر محصول فقط رنگ یا سایز دارد، پردازش‌های خاص انجام می‌دهیم
    const isOnlyColorProduct = Object.keys(productData.color_to_sizes).length > 0 && Object.keys(productData.size_to_colors).length === 0;
    const isOnlySizeProduct = Object.keys(productData.size_to_colors).length > 0 && Object.keys(productData.color_to_sizes).length === 0;
    const isNoColorOrSize = Object.keys(productData.color_to_sizes).length === 0 && Object.keys(productData.size_to_colors).length === 0;

    // اگر محصول هیچ رنگ یا سایزی ندارد
    if (isNoColorOrSize) {
      console.error(`رنگ یا سایز برای محصول ${productId} موجود نیست`);
      return;
    }

    // تابع آپدیت قیمت و موجودی
    function updatePriceAndStock() {
      const selectedColorInput = pkg.querySelector(`input[name="color-${productId}"]:checked`);
      const selectedSizeInput = pkg.querySelector(`input[name="size-${productId}"]:checked`);

      if (!selectedColorInput && isOnlyColorProduct) {
        priceContainer.innerHTML = "قیمت نامشخص";
        stockContainer.innerHTML = "موجودی نامشخص";
        return;
      }

      if (!selectedColorInput && isOnlySizeProduct && selectedSizeInput) {
        const selectedSize = selectedSizeInput.value;

        const variants = productData?.variants || [];
        const matchedVariant = variants.find((v) => v.sizes.includes(selectedSize));

        if (matchedVariant) {
          priceContainer.innerHTML = `<span class="theme-color">${matchedVariant.price.toLocaleString('fa-IR')} تومان</span>`;

          if (matchedVariant.stock <= 10) {
            let stockText = `${matchedVariant.stock} عدد در انبار باقی مانده`;
            let classes = 'low-stock';

            if (matchedVariant.stock < 10) {
              classes += ' blinking';
            }

            stockContainer.innerHTML = `<span class="${classes}">${stockText}</span>`;
          } else {
            stockContainer.innerHTML = ''; // نمایش نده
          }
        } else {
          priceContainer.innerHTML = "قیمت موجود نیست";
          stockContainer.innerHTML = "موجودی موجود نیست";
        }

        return;
      }

      const selectedColor = selectedColorInput ? selectedColorInput.dataset.colorId : null;
      const selectedSize = selectedSizeInput ? selectedSizeInput.value : null;

      const variants = productData?.variants || [];
      const matchedVariant = variants.find((v) => {
        const colorMatch = selectedColor ? v.color === selectedColor : true;
        const sizeMatch = selectedSize ? v.sizes.includes(selectedSize) : true;
        return colorMatch && sizeMatch;
      });

      if (matchedVariant) {
        priceContainer.innerHTML = `<span class="theme-color">${matchedVariant.price.toLocaleString('fa-IR')} تومان</span>`;

        if (matchedVariant.stock <= 10) {
          let stockText = `${matchedVariant.stock} عدد در انبار باقی مانده`;
          let classes = 'low-stock';

          if (matchedVariant.stock < 10) {
            classes += ' blinking';
          }

          stockContainer.innerHTML = `<span class="${classes}">${stockText}</span>`;
        } else {
          stockContainer.innerHTML = ''; // نمایش نده
        }
      } else {
        priceContainer.innerHTML = "قیمت موجود نیست";
        stockContainer.innerHTML = "موجودی موجود نیست";
      }
    }

    // تابع محدودسازی سایزها براساس رنگ انتخاب‌شده
    function updateSizeOptionsByColor() {
      const selectedColorInput = pkg.querySelector(`input[name="color-${productId}"]:checked`);
      if (!selectedColorInput) return;

      const selectedColor = selectedColorInput.dataset.colorId;
      const availableSizes = productData.color_to_sizes[selectedColor] || [];

      sizeInputs.forEach((sizeInput) => {
        if (availableSizes.includes(sizeInput.value)) {
          sizeInput.parentElement.style.display = "inline-block"; // یا flex
          sizeInput.disabled = false;
        } else {
          sizeInput.checked = false;
          sizeInput.parentElement.style.display = "none";
          sizeInput.disabled = true;
        }
      });

      updatePriceAndStock(); // چون ممکنه سایز غیرفعال شده باشه
    }

    // اگر محصول فقط رنگ دارد، بخش سایز را مخفی کنیم
    if (isOnlyColorProduct) {
      sizeInputs.forEach((sizeInput) => {
        sizeInput.parentElement.style.display = "none";
        sizeInput.disabled = true;
      });
      updatePriceAndStock();
    }

    // اگر محصول فقط سایز دارد، بخش رنگ را مخفی کنیم
    if (isOnlySizeProduct) {
      colorInputs.forEach((colorInput) => {
        colorInput.parentElement.style.display = "none";
        colorInput.disabled = true;
      });
      updatePriceAndStock();
    }

    // اگر هیچ رنگ یا سایز نداریم، خطا می‌دهیم
    if (isNoColorOrSize) {
      priceContainer.innerHTML = "قیمت نامشخص";
      stockContainer.innerHTML = "موجودی نامشخص";
      return;
    }

    // رویدادها
    colorInputs.forEach((input) => {
      input.addEventListener("change", () => {
        updateSizeOptionsByColor();
        updatePriceAndStock(); // به محض تغییر رنگ قیمت و موجودی رو بروزرسانی می‌کنیم
      });
    });

    sizeInputs.forEach((input) => {
      input.addEventListener("change", updatePriceAndStock);
    });

    // اجرای اولیه
    updateSizeOptionsByColor();
    updatePriceAndStock();
  });
});






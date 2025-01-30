
$(document).ready(function(){
    const Toast = Swal.mixin({
        toast: true,
        position:"top",
        showConfirmationButton: false,
        timer: 2000,
        timerProgressBar: true,
    })
    function generateCartId(){
        const ls_cartid = localStorage.getItem("cartId")

        if(ls_cartid == null){
            var cartId = "";

            for(var i=0; i<10;i++){
                cartId += Math.floor(Math.random()*10)
            }

            localStorage.setItem("cartId",cartId);
        }

        return ls_cartid || cartId
    }

    $(document).on("click",".add_to_cart", function(){
        const button_el = $(this)
        const id = button_el.attr("data-id")
        const qty =$(".quantity").val()
        const size = $("input[name='size']:checked").val(); 
        const color = $("input[name='color']:checked").val();

        const cart_id =generateCartId()

          $.ajax({
            url: "/add_to_cart",
            data:{
                id:id,
                qty:qty,
                size:size,
                color:color,
                cart_id:cart_id,
            },

            beforeSend: function(){
                button_el.html("Adding to Cart <i class='fas fa-spinner fa-spin ms-2'></i>");
            },
            success:function(response){
                console.log(response);
                Toast.fire({
                    icon:"success",
                    title: response?.message,
                });
                button_el.html("Add to Cart <i class='fas fa-shopping-cart ms-2'></i>");
                $(".total_cart_items").text(response?.total_cart_items);
            },
            error: function(xhr,status,error){
                console.log("Error status: ",xhr.status);
                console.log("Response Text: ",xhr.responseText);

                let errorResponse = JSON.parse(xhr.responseText);
                Toast.fire({
                    icon:"success",
                    title: errorResponse?.error,
                });
            }

          })
    })
})
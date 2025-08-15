# E-commerce Extension Example

This example demonstrates how to extend the Generic API Framework to build an e-commerce application. It shows advanced patterns for complex business logic, relationships, and domain modeling.

## Overview

This extension adds:
- **Product Catalog**: Products, categories, and inventory management
- **Shopping Cart**: Session-based and persistent cart functionality
- **Order Management**: Order processing and fulfillment
- **Customer Management**: Customer profiles and addresses
- **Payment Processing**: Payment integration patterns

## Core Models

### Product Management
```python
class Product(Base, SoftDeleteMixin, AuditMixin):
    """Product model with comprehensive e-commerce features."""
    
    # Basic information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    short_description: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    compare_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    
    # Inventory
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    barcode: Mapped[Optional[str]] = mapped_column(String(100))
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True)
    inventory_quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10)
    
    # Physical properties
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3))
    dimensions: Mapped[Optional[str]] = mapped_column(String(100))  # "L x W x H"
    
    # Status and visibility
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_shipping: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(String(60))
    meta_description: Mapped[Optional[str]] = mapped_column(String(160))
    
    # Relationships
    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('product_category.id'))
    brand_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('brand.id'))
    
    category: Mapped[Optional["ProductCategory"]] = relationship("ProductCategory")
    brand: Mapped[Optional["Brand"]] = relationship("Brand")
    variants: Mapped[List["ProductVariant"]] = relationship("ProductVariant")
    images: Mapped[List["ProductImage"]] = relationship("ProductImage")
    reviews: Mapped[List["ProductReview"]] = relationship("ProductReview")

class ProductCategory(Base, SoftDeleteMixin):
    """Hierarchical product categories."""
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Hierarchy
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('product_category.id'))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    parent: Mapped[Optional["ProductCategory"]] = relationship("ProductCategory", remote_side="ProductCategory.id")
    children: Mapped[List["ProductCategory"]] = relationship("ProductCategory")
    products: Mapped[List[Product]] = relationship("Product")
```

### Order Management
```python
class Order(Base, AuditMixin):
    """Order model with comprehensive e-commerce features."""
    
    # Order identification
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # Customer information
    customer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('customer.id'))
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Order status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    fulfillment_status: Mapped[str] = mapped_column(String(20), default="unfulfilled")
    payment_status: Mapped[str] = mapped_column(String(20), default="pending")
    
    # Financial information
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Addresses (stored as JSON for flexibility)
    billing_address: Mapped[Dict] = mapped_column(JSON)
    shipping_address: Mapped[Dict] = mapped_column(JSON)
    
    # Timestamps
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order")
    payments: Mapped[List["Payment"]] = relationship("Payment")

class OrderItem(Base):
    """Individual items within an order."""
    
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey('order.id'), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey('product.id'), nullable=False)
    variant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('product_variant.id'))
    
    # Product snapshot (at time of order)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_sku: Mapped[str] = mapped_column(String(100), nullable=False)
    variant_title: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Pricing and quantity
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="items")
    product: Mapped[Product] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
```

## Business Logic Services

### ProductService
```python
class ProductService(CRUDService):
    """Advanced product management with inventory tracking."""
    
    async def create_product(self, data: ProductCreate) -> Product:
        """Create product with automatic SKU generation."""
        # Generate SKU if not provided
        if not data.sku:
            data.sku = await self._generate_sku(data.name)
        
        # Generate slug from name
        data.slug = self._generate_slug(data.name)
        
        # Validate business rules
        await self._validate_product_data(data)
        
        return await super().create(data)
    
    async def update_inventory(self, product_id: str, quantity_change: int, reason: str = "manual") -> Product:
        """Update product inventory with audit trail."""
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")
        
        if not product.track_inventory:
            raise ValidationError("Product does not track inventory")
        
        new_quantity = product.inventory_quantity + quantity_change
        
        if new_quantity < 0:
            raise ValidationError(f"Insufficient inventory. Available: {product.inventory_quantity}")
        
        # Update inventory
        updated_product = await self.repository.update(
            product_id,
            inventory_quantity=new_quantity
        )
        
        # Log inventory change
        await self._log_inventory_change(product_id, quantity_change, reason)
        
        # Check for low stock alert
        if new_quantity <= product.low_stock_threshold:
            await self._trigger_low_stock_alert(product)
        
        return updated_product
    
    async def get_low_stock_products(self) -> List[Product]:
        """Get products with low stock levels."""
        return await self.repository.filter_by(
            track_inventory=True,
            inventory_quantity__lte=F('low_stock_threshold'),
            is_active=True
        )
    
    async def _generate_sku(self, name: str) -> str:
        """Generate unique SKU from product name."""
        base_sku = ''.join(word[:3].upper() for word in name.split()[:3])
        counter = 1
        
        while True:
            sku = f"{base_sku}{counter:03d}"
            existing = await self.repository.get_by_field("sku", sku)
            if not existing:
                return sku
            counter += 1
```

### OrderService
```python
class OrderService(CRUDService):
    """Comprehensive order management with state transitions."""
    
    def __init__(self, order_repository, product_service, payment_service):
        super().__init__(order_repository)
        self.product_service = product_service
        self.payment_service = payment_service
    
    async def create_order_from_cart(self, cart: ShoppingCart, customer_info: CustomerInfo) -> Order:
        """Create order from shopping cart with inventory reservation."""
        # Validate cart items availability
        await self._validate_cart_availability(cart)
        
        # Calculate totals
        subtotal = sum(item.quantity * item.unit_price for item in cart.items)
        tax_amount = await self._calculate_tax(subtotal, customer_info.billing_address)
        shipping_amount = await self._calculate_shipping(cart, customer_info.shipping_address)
        total_amount = subtotal + tax_amount + shipping_amount
        
        # Create order
        order_data = {
            "order_number": await self._generate_order_number(),
            "customer_email": customer_info.email,
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "shipping_amount": shipping_amount,
            "total_amount": total_amount,
            "billing_address": customer_info.billing_address.dict(),
            "shipping_address": customer_info.shipping_address.dict(),
            "status": "pending"
        }
        
        order = await self.repository.create(**order_data)
        
        # Create order items and reserve inventory
        for cart_item in cart.items:
            await self._create_order_item(order.id, cart_item)
            await self.product_service.update_inventory(
                cart_item.product_id, 
                -cart_item.quantity, 
                f"Reserved for order {order.order_number}"
            )
        
        return order
    
    async def process_payment(self, order_id: str, payment_data: PaymentData) -> Order:
        """Process payment for an order."""
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        
        if order.payment_status != "pending":
            raise ValidationError("Order payment already processed")
        
        try:
            # Process payment through payment service
            payment_result = await self.payment_service.process_payment(
                amount=order.total_amount,
                payment_data=payment_data
            )
            
            # Update order status
            await self.repository.update(order_id, 
                payment_status="paid",
                status="confirmed"
            )
            
            # Create payment record
            await self._create_payment_record(order_id, payment_result)
            
            return await self.repository.get_by_id(order_id)
            
        except PaymentError as e:
            # Handle payment failure
            await self.repository.update(order_id, 
                payment_status="failed",
                status="cancelled"
            )
            
            # Release reserved inventory
            await self._release_order_inventory(order)
            
            raise ValidationError(f"Payment failed: {e}")
    
    async def fulfill_order(self, order_id: str, tracking_number: str = None) -> Order:
        """Mark order as fulfilled and shipped."""
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        
        if order.status != "confirmed":
            raise ValidationError("Order must be confirmed before fulfillment")
        
        update_data = {
            "fulfillment_status": "fulfilled",
            "status": "shipped",
            "shipped_at": datetime.utcnow()
        }
        
        if tracking_number:
            update_data["tracking_number"] = tracking_number
        
        return await self.repository.update(order_id, **update_data)
```

## Advanced API Patterns

### Product Search and Filtering
```python
@router.get("/products/search", response_model=ProductSearchResponse)
async def search_products(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Category slug"),
    brand: Optional[str] = Query(None, description="Brand slug"),
    min_price: Optional[Decimal] = Query(None, ge=0),
    max_price: Optional[Decimal] = Query(None, ge=0),
    in_stock: bool = Query(True, description="Only show in-stock products"),
    sort_by: str = Query("relevance", regex="^(relevance|price_asc|price_desc|newest|rating)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Advanced product search with filtering and sorting."""
    filters = {}
    
    if q:
        filters["search"] = q
    if category:
        filters["category__slug"] = category
    if brand:
        filters["brand__slug"] = brand
    if min_price is not None:
        filters["price__gte"] = min_price
    if max_price is not None:
        filters["price__lte"] = max_price
    if in_stock:
        filters["inventory_quantity__gt"] = 0
    
    return await product_service.search_products(
        filters=filters,
        sort_by=sort_by,
        skip=skip,
        limit=limit
    )
```

### Order Management API
```python
@router.post("/orders", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new order from cart."""
    return await order_service.create_order_from_cart(
        cart=order_data.cart,
        customer_info=order_data.customer_info
    )

@router.post("/orders/{order_id}/payment", response_model=OrderResponse)
async def process_order_payment(
    order_id: str,
    payment_data: PaymentData,
    current_user: User = Depends(get_current_user)
):
    """Process payment for an order."""
    return await order_service.process_payment(order_id, payment_data)

@router.patch("/orders/{order_id}/fulfill", response_model=OrderResponse)
async def fulfill_order(
    order_id: str,
    fulfillment_data: FulfillmentData,
    current_user: User = Depends(require_admin)
):
    """Mark order as fulfilled (admin only)."""
    return await order_service.fulfill_order(
        order_id, 
        fulfillment_data.tracking_number
    )
```

## Key E-commerce Patterns

### 1. Inventory Management
```python
class InventoryService:
    """Service for managing product inventory."""
    
    async def reserve_inventory(self, items: List[CartItem]) -> List[InventoryReservation]:
        """Reserve inventory for order processing."""
        reservations = []
        
        for item in items:
            product = await self.product_service.get_by_id(item.product_id)
            
            if product.track_inventory and product.inventory_quantity < item.quantity:
                raise InsufficientInventoryError(
                    f"Only {product.inventory_quantity} units of {product.name} available"
                )
            
            reservation = await self._create_reservation(item)
            reservations.append(reservation)
        
        return reservations
    
    async def commit_reservations(self, reservations: List[InventoryReservation]):
        """Commit inventory reservations (reduce actual inventory)."""
        for reservation in reservations:
            await self.product_service.update_inventory(
                reservation.product_id,
                -reservation.quantity,
                f"Order {reservation.order_id} committed"
            )
```

### 2. Price Calculation
```python
class PricingService:
    """Service for calculating prices, taxes, and shipping."""
    
    async def calculate_order_total(self, cart: ShoppingCart, address: Address) -> OrderTotals:
        """Calculate comprehensive order totals."""
        subtotal = sum(item.quantity * item.unit_price for item in cart.items)
        
        # Apply discounts
        discount_amount = await self._calculate_discounts(cart)
        discounted_subtotal = subtotal - discount_amount
        
        # Calculate tax
        tax_amount = await self._calculate_tax(discounted_subtotal, address)
        
        # Calculate shipping
        shipping_amount = await self._calculate_shipping(cart, address)
        
        total = discounted_subtotal + tax_amount + shipping_amount
        
        return OrderTotals(
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            total=total
        )
```

### 3. Payment Processing
```python
class PaymentService:
    """Service for processing payments."""
    
    async def process_payment(self, amount: Decimal, payment_data: PaymentData) -> PaymentResult:
        """Process payment through configured payment gateway."""
        gateway = self._get_payment_gateway(payment_data.method)
        
        try:
            result = await gateway.charge(
                amount=amount,
                payment_method=payment_data.payment_method,
                customer_info=payment_data.customer_info
            )
            
            return PaymentResult(
                success=True,
                transaction_id=result.transaction_id,
                gateway_response=result.raw_response
            )
            
        except PaymentGatewayError as e:
            return PaymentResult(
                success=False,
                error_message=str(e),
                error_code=e.code
            )
```

## Testing E-commerce Logic

```python
class TestOrderService:
    @pytest.mark.asyncio
    async def test_create_order_from_cart(self, order_service, sample_cart):
        """Test order creation from shopping cart."""
        customer_info = CustomerInfoFactory()
        
        order = await order_service.create_order_from_cart(sample_cart, customer_info)
        
        assert order.order_number is not None
        assert order.total_amount > 0
        assert len(order.items) == len(sample_cart.items)
        assert order.status == "pending"
    
    @pytest.mark.asyncio
    async def test_insufficient_inventory_fails(self, order_service):
        """Test that orders fail when inventory is insufficient."""
        cart = ShoppingCartFactory()
        cart.items = [CartItemFactory(quantity=100)]  # More than available
        
        with pytest.raises(InsufficientInventoryError):
            await order_service.create_order_from_cart(cart, CustomerInfoFactory())
    
    @pytest.mark.asyncio
    async def test_payment_processing(self, order_service, mock_payment_service):
        """Test successful payment processing."""
        order = OrderFactory(status="pending", payment_status="pending")
        payment_data = PaymentDataFactory()
        
        mock_payment_service.process_payment.return_value = PaymentResult(success=True)
        
        processed_order = await order_service.process_payment(order.id, payment_data)
        
        assert processed_order.payment_status == "paid"
        assert processed_order.status == "confirmed"
```

This e-commerce extension demonstrates how the framework can be extended to handle complex business logic, multiple related entities, and sophisticated workflows while maintaining clean architecture and testability.
# Extending the Generic API Framework

This guide shows you how to extend the generic API framework for your specific application domain. The framework provides a solid foundation with common patterns that you can build upon.

## Overview

The framework is designed to be extended through:
- **Domain Models**: Add your specific data models
- **Business Logic**: Implement your domain-specific services
- **API Endpoints**: Create controllers and routes for your use cases
- **Configuration**: Customize settings for your application
- **Validation**: Add domain-specific validation rules

## Adding New Domain Models

### 1. Create Your Model

Add your domain model to `src/database/models.py`:

```python
class Product(Base, SoftDeleteMixin, AuditMixin):
    """Product model for an e-commerce application."""
    
    # Basic product information
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Product name"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Product description"
    )
    
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Product price"
    )
    
    # Inventory
    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Available stock"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Product active status"
    )
    
    # Category relationship (many-to-one)
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey('category.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment="Product category"
    )
    
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="products",
        lazy="selectin"
    )

class Category(Base, SoftDeleteMixin, AuditMixin):
    """Category model for organizing products."""
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Category name"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Category description"
    )
    
    # Relationships
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
```

### 2. Create Migration

Generate and apply the database migration:

```bash
poetry run alembic revision --autogenerate -m "Add Product and Category models"
poetry run alembic upgrade head
```

### 3. Update Database Module

Add your models to `src/database/__init__.py`:

```python
from .models import User, Post, UserStatus, Product, Category
```

## Creating Domain-Specific Schemas

### 1. Create Pydantic Schemas

Add schemas in `src/schemas/products.py`:

```python
from decimal import Decimal
from typing import Optional, List
from pydantic import Field, field_validator
from src.schemas.base import BaseSchema, IdentifierMixin, TimestampMixin

class ProductBase(BaseSchema):
    """Base product schema."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Product name"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Product description"
    )
    price: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Product price"
    )
    stock_quantity: int = Field(
        default=0,
        ge=0,
        description="Available stock"
    )
    category_id: Optional[str] = Field(
        None,
        description="Category ID"
    )

class ProductCreate(ProductBase):
    """Schema for creating products."""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate product name."""
        if not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip()

class ProductUpdate(BaseSchema):
    """Schema for updating products."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    category_id: Optional[str] = None

class Product(ProductBase, IdentifierMixin, TimestampMixin):
    """Product response schema."""
    
    is_active: bool
    category: Optional["Category"] = None

class Category(BaseSchema, IdentifierMixin, TimestampMixin):
    """Category response schema."""
    
    name: str
    description: Optional[str]
    product_count: int = Field(default=0, description="Number of products in category")
```

## Implementing Business Logic

### 1. Create Domain Service

Add business logic in `src/services/products.py`:

```python
from typing import List, Optional, Dict, Any
from decimal import Decimal
from src.services.base import CRUDService, ValidationError, NotFoundError
from src.database.repositories import BaseRepository
from src.schemas.products import ProductCreate, ProductUpdate, Product

class ProductService(CRUDService):
    """Business logic for product management."""
    
    def __init__(self, product_repository: BaseRepository):
        super().__init__(product_repository)
    
    async def create(self, data: ProductCreate) -> Product:
        """Create a new product with business validation."""
        self._log_operation("create", "product", name=data.name)
        
        # Business rule: Check for duplicate product names
        existing = await self.repository.get_by_field("name", data.name)
        if existing:
            raise ValidationError(f"Product with name '{data.name}' already exists")
        
        # Business rule: Validate category exists if provided
        if data.category_id:
            await self._validate_category_exists(data.category_id)
        
        # Create product
        product_data = data.model_dump()
        product = await self.repository.create(**product_data)
        
        return Product.model_validate(product)
    
    async def update_stock(self, product_id: str, quantity_change: int) -> Product:
        """Update product stock with business rules."""
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")
        
        new_quantity = product.stock_quantity + quantity_change
        
        # Business rule: Stock cannot go negative
        if new_quantity < 0:
            raise ValidationError(
                f"Insufficient stock. Available: {product.stock_quantity}, "
                f"Requested: {abs(quantity_change)}"
            )
        
        updated_product = await self.repository.update(
            product_id, 
            stock_quantity=new_quantity
        )
        
        return Product.model_validate(updated_product)
    
    async def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """Get products with low stock levels."""
        products = await self.repository.filter_by(
            stock_quantity__lt=threshold,
            is_active=True
        )
        
        return [Product.model_validate(p) for p in products]
    
    async def _validate_category_exists(self, category_id: str) -> None:
        """Validate that category exists."""
        # This would use a category repository in a real implementation
        pass
```

### 2. Create Repository

Add repository in `src/database/repositories.py`:

```python
class ProductRepository(BaseRepository[Product]):
    """Repository for Product model operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Product)
    
    async def get_by_name(self, name: str) -> Optional[Product]:
        """Get product by name."""
        result = await self.session.execute(
            select(Product).where(Product.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_by_category(self, category_id: str) -> List[Product]:
        """Get products by category."""
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.category_id == category_id)
            .where(Product.is_active == True)
        )
        return list(result.scalars().all())
    
    async def get_low_stock(self, threshold: int = 10) -> List[Product]:
        """Get products with stock below threshold."""
        result = await self.session.execute(
            select(Product)
            .where(Product.stock_quantity < threshold)
            .where(Product.is_active == True)
            .order_by(Product.stock_quantity.asc())
        )
        return list(result.scalars().all())
```

## Creating API Endpoints

### 1. Create Controller

Add controller in `src/controllers/products.py`:

```python
from typing import List, Optional, Dict, Any
from src.controllers.base import CRUDController
from src.services.products import ProductService
from src.schemas.products import Product, ProductCreate, ProductUpdate

class ProductController(CRUDController[Product, ProductCreate, ProductUpdate]):
    """Controller for product operations."""
    
    def __init__(self, product_service: ProductService):
        super().__init__(Product)
        self.product_service = product_service
    
    async def create(self, data: ProductCreate) -> Product:
        """Create a new product."""
        self._log_request("POST", "/products")
        
        try:
            product = await self.product_service.create(data)
            self._log_response("POST", "/products", 201)
            return product
        except Exception as e:
            raise self._handle_error(e, "create_product")
    
    async def update_stock(self, product_id: str, quantity_change: int) -> Product:
        """Update product stock."""
        self._log_request("PATCH", f"/products/{product_id}/stock")
        
        try:
            product = await self.product_service.update_stock(product_id, quantity_change)
            self._log_response("PATCH", f"/products/{product_id}/stock", 200)
            return product
        except Exception as e:
            raise self._handle_error(e, f"update_stock_{product_id}")
    
    async def get_low_stock(self, threshold: int = 10) -> List[Product]:
        """Get products with low stock."""
        self._log_request("GET", "/products/low-stock")
        
        try:
            products = await self.product_service.get_low_stock_products(threshold)
            self._log_response("GET", "/products/low-stock", 200, count=len(products))
            return products
        except Exception as e:
            raise self._handle_error(e, "get_low_stock_products")
```

### 2. Create Routes

Add routes in `src/routes/v1/products.py`:

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from src.controllers.products import ProductController
from src.schemas.products import Product, ProductCreate, ProductUpdate
from src.dependencies import get_product_controller

router = APIRouter(
    prefix="/products",
    tags=["products"],
)

@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    controller: ProductController = Depends(get_product_controller)
) -> Product:
    """Create a new product."""
    return await controller.create(product_data)

@router.get("/", response_model=List[Product])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    controller: ProductController = Depends(get_product_controller)
) -> List[Product]:
    """List products with pagination."""
    result = await controller.get_all(skip=skip, limit=limit)
    return result["items"]

@router.get("/low-stock", response_model=List[Product])
async def get_low_stock_products(
    threshold: int = Query(10, ge=1, le=100),
    controller: ProductController = Depends(get_product_controller)
) -> List[Product]:
    """Get products with low stock levels."""
    return await controller.get_low_stock(threshold)

@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: str,
    controller: ProductController = Depends(get_product_controller)
) -> Product:
    """Get a product by ID."""
    product = await controller.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch("/{product_id}/stock")
async def update_product_stock(
    product_id: str,
    quantity_change: int,
    controller: ProductController = Depends(get_product_controller)
) -> Product:
    """Update product stock quantity."""
    return await controller.update_stock(product_id, quantity_change)
```

### 3. Register Routes

Add to your main API router in `src/routes/v1/api.py`:

```python
from src.routes.v1 import products

router.include_router(products.router)
```

## Adding Configuration

### 1. Add Settings

Add your configuration to `config/settings.toml`:

```toml
# Product management settings
product_low_stock_threshold = 10
product_max_price = 10000.00
product_image_max_size = 5242880  # 5MB

# Inventory settings
inventory_auto_reorder = false
inventory_reorder_threshold = 5
```

### 2. Use in Code

Access configuration in your services:

```python
from src.config.settings import settings

class ProductService(CRUDService):
    def __init__(self, product_repository: BaseRepository):
        super().__init__(product_repository)
        self.low_stock_threshold = getattr(settings, "product_low_stock_threshold", 10)
        self.max_price = getattr(settings, "product_max_price", 10000.00)
```

## Adding Custom Validation

### 1. Domain-Specific Validators

Add custom validators to your schemas:

```python
from pydantic import field_validator
import re

class ProductCreate(ProductBase):
    @field_validator('name')
    @classmethod
    def validate_product_name(cls, v: str) -> str:
        """Validate product name follows business rules."""
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError("Product name can only contain letters, numbers, spaces, hyphens, and underscores")
        
        # Business rule: No profanity (simplified example)
        forbidden_words = ['spam', 'fake', 'counterfeit']
        if any(word in v.lower() for word in forbidden_words):
            raise ValueError("Product name contains forbidden words")
        
        return v.strip()
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate price follows business rules."""
        if v <= 0:
            raise ValueError("Price must be greater than zero")
        
        if v > Decimal('10000.00'):
            raise ValueError("Price cannot exceed $10,000")
        
        return v
```

## Testing Your Extensions

### 1. Create Tests

Add tests in `tests/unit/test_products.py`:

```python
import pytest
from decimal import Decimal
from src.services.products import ProductService
from src.schemas.products import ProductCreate
from tests.factories import ProductFactory

class TestProductService:
    @pytest.fixture
    def product_service(self, mock_product_repository):
        return ProductService(mock_product_repository)
    
    @pytest.mark.asyncio
    async def test_create_product(self, product_service):
        """Test product creation."""
        product_data = ProductCreate(
            name="Test Product",
            description="A test product",
            price=Decimal("29.99"),
            stock_quantity=100
        )
        
        product = await product_service.create(product_data)
        
        assert product.name == "Test Product"
        assert product.price == Decimal("29.99")
        assert product.stock_quantity == 100
    
    @pytest.mark.asyncio
    async def test_update_stock_insufficient(self, product_service):
        """Test stock update with insufficient quantity."""
        # Setup existing product with low stock
        existing_product = ProductFactory(stock_quantity=5)
        product_service.repository.get_by_id.return_value = existing_product
        
        # Try to reduce stock by more than available
        with pytest.raises(ValidationError, match="Insufficient stock"):
            await product_service.update_stock("product_123", -10)
```

### 2. Create Factories

Add test factories in `tests/factories.py`:

```python
class ProductFactory(factory.Factory):
    """Factory for creating Product test objects."""
    
    class Meta:
        model = MockProduct
    
    id = factory.LazyFunction(lambda: str(uuid4()))
    name = factory.Faker('word')
    description = factory.Faker('text', max_nb_chars=200)
    price = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    stock_quantity = factory.Faker('random_int', min=0, max=1000)
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
```

## Best Practices

### 1. Follow Framework Patterns

- **Use base classes**: Extend `BaseService`, `CRUDController`, etc.
- **Follow naming conventions**: Use consistent naming across your domain
- **Implement proper validation**: Use Pydantic validators and business rules
- **Add comprehensive tests**: Test both happy path and error cases

### 2. Domain Modeling

- **Start simple**: Begin with basic models and add complexity gradually
- **Use relationships wisely**: Model real-world relationships but avoid over-complexity
- **Consider performance**: Add indexes for frequently queried fields
- **Plan for growth**: Design models that can evolve with your business

### 3. API Design

- **RESTful endpoints**: Follow REST conventions for consistency
- **Proper HTTP status codes**: Use appropriate status codes for different scenarios
- **Comprehensive documentation**: Document your endpoints with examples
- **Version your APIs**: Plan for API evolution from the start

### 4. Configuration Management

- **Environment-specific settings**: Use different configs for dev/staging/prod
- **Secure secrets**: Never commit secrets to version control
- **Validate configuration**: Add validation for critical settings
- **Document settings**: Explain what each setting does

## Example: Complete E-commerce Extension

Here's how you might extend the framework for a complete e-commerce application:

```
src/
├── models/
│   ├── products.py      # Product, Category, Brand models
│   ├── orders.py        # Order, OrderItem models
│   ├── customers.py     # Customer, Address models
│   └── inventory.py     # Stock, Warehouse models
├── services/
│   ├── product_service.py
│   ├── order_service.py
│   ├── inventory_service.py
│   └── payment_service.py
├── controllers/
│   ├── products.py
│   ├── orders.py
│   └── customers.py
├── schemas/
│   ├── products.py
│   ├── orders.py
│   └── customers.py
└── routes/v1/
    ├── products.py
    ├── orders.py
    └── customers.py
```

This structure follows the framework patterns while implementing domain-specific functionality for e-commerce.

## Getting Help

- **Study the examples**: Look at the User and Post models for patterns
- **Read the base classes**: Understand what functionality is already provided
- **Check the tests**: See how existing functionality is tested
- **Follow conventions**: Use the same patterns as the existing code
- **Start small**: Begin with simple extensions and build complexity gradually

The framework is designed to be flexible and extensible. By following these patterns, you can build robust, maintainable applications for any domain.
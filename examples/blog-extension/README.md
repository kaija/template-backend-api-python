# Blog Extension Example

This example shows how to extend the Generic API Framework to create a simple blog application. It demonstrates common patterns for adding domain-specific functionality.

## Overview

This extension adds:
- **Blog Posts**: Content management with categories and tags
- **Comments**: User comments on blog posts
- **Categories**: Organization of blog content
- **Tags**: Flexible content labeling

## Models Added

### BlogPost Model
```python
class BlogPost(Base, SoftDeleteMixin, AuditMixin):
    """Blog post model."""
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Publishing
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(String(60))
    meta_description: Mapped[Optional[str]] = mapped_column(String(160))
    
    # Relationships
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey('user.id'))
    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('blog_category.id'))
    
    author: Mapped[User] = relationship("User", lazy="selectin")
    category: Mapped[Optional["BlogCategory"]] = relationship("BlogCategory")
    comments: Mapped[List["BlogComment"]] = relationship("BlogComment", back_populates="post")
    tags: Mapped[List["BlogTag"]] = relationship("BlogTag", secondary="blog_post_tags")
```

### BlogCategory Model
```python
class BlogCategory(Base, SoftDeleteMixin):
    """Blog category model."""
    
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    posts: Mapped[List[BlogPost]] = relationship("BlogPost", back_populates="category")
```

## Business Logic

### BlogService
```python
class BlogService(CRUDService):
    """Business logic for blog operations."""
    
    async def publish_post(self, post_id: str) -> BlogPost:
        """Publish a blog post."""
        post = await self.repository.get_by_id(post_id)
        if not post:
            raise NotFoundError("Post not found")
        
        if post.is_published:
            raise ValidationError("Post is already published")
        
        # Business rule: Must have title and content
        if not post.title or not post.content:
            raise ValidationError("Post must have title and content to publish")
        
        # Set publication date
        post.is_published = True
        post.published_at = datetime.utcnow()
        
        return await self.repository.update(post_id, **post.__dict__)
    
    async def get_published_posts(self, limit: int = 10) -> List[BlogPost]:
        """Get published posts ordered by publication date."""
        return await self.repository.filter_by(
            is_published=True,
            order_by="-published_at",
            limit=limit
        )
```

## API Endpoints

### Blog Routes
```python
@router.get("/posts", response_model=List[BlogPostResponse])
async def list_blog_posts(
    published_only: bool = Query(True),
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50)
):
    """List blog posts with filtering."""
    filters = {"is_published": published_only} if published_only else {}
    
    if category:
        filters["category__slug"] = category
    if tag:
        filters["tags__slug"] = tag
    
    return await blog_service.get_all(skip=skip, limit=limit, filters=filters)

@router.post("/posts/{post_id}/publish", response_model=BlogPostResponse)
async def publish_post(post_id: str):
    """Publish a blog post."""
    return await blog_service.publish_post(post_id)
```

## Key Patterns Demonstrated

### 1. Slug Generation
```python
def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title."""
    import re
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')
```

### 2. SEO Fields
```python
class BlogPostCreate(BaseSchema):
    title: str
    content: str
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if len(v) > 60:
            raise ValueError("Title should be under 60 characters for SEO")
        return v
```

### 3. Content Validation
```python
@field_validator('content')
@classmethod
def validate_content(cls, v: str) -> str:
    # Remove dangerous HTML tags
    import bleach
    allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'h1', 'h2', 'h3']
    return bleach.clean(v, tags=allowed_tags, strip=True)
```

## Usage Example

```python
# Create a blog post
post_data = BlogPostCreate(
    title="Getting Started with FastAPI",
    content="<p>FastAPI is a modern web framework...</p>",
    category_id="tech_category_id",
    tags=["python", "fastapi", "tutorial"]
)

post = await blog_service.create(post_data)

# Publish the post
published_post = await blog_service.publish_post(post.id)

# Get published posts
recent_posts = await blog_service.get_published_posts(limit=5)
```

## Testing

```python
class TestBlogService:
    @pytest.mark.asyncio
    async def test_publish_post(self, blog_service):
        """Test publishing a blog post."""
        # Create draft post
        post_data = BlogPostCreate(
            title="Test Post",
            content="Test content"
        )
        post = await blog_service.create(post_data)
        
        # Publish it
        published = await blog_service.publish_post(post.id)
        
        assert published.is_published is True
        assert published.published_at is not None
    
    @pytest.mark.asyncio
    async def test_publish_empty_post_fails(self, blog_service):
        """Test that empty posts cannot be published."""
        post = BlogPostFactory(title="", content="")
        
        with pytest.raises(ValidationError):
            await blog_service.publish_post(post.id)
```

## Migration

```python
"""Add blog models

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000
"""

def upgrade() -> None:
    # Create blog_category table
    op.create_table('blog_category',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    
    # Create blog_post table
    op.create_table('blog_post',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(250), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_published', sa.Boolean(), default=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('author_id', sa.String(36), nullable=False),
        sa.Column('category_id', sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['user.id']),
        sa.ForeignKeyConstraint(['category_id'], ['blog_category.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
```

This example shows how the framework's patterns can be extended to create a full-featured blog system while maintaining consistency with the base architecture.